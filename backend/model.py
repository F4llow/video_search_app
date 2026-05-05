"""
model.py — Qwen2.5-Omni-7B inference module

Handles model loading and video summarization via the official
qwen-omni-utils pipeline with full TMRoPE-aligned audio+video processing.
"""

import os
import gc
import logging
import torch
from pathlib import Path

logger = logging.getLogger(__name__)

# Global model state — loaded once, reused across requests
_model = None
_processor = None
_model_load_error = None

MODEL_ID = "Qwen/Qwen2.5-Omni-7B"

# System prompt focused on text-only output (Talker is disabled).
# When not generating audio, we use a simpler system prompt.
SYSTEM_PROMPT = (
    "You are an expert video analyst. Analyze the provided video comprehensively, "
    "paying close attention to both what you see (visual content) and what you hear "
    "(audio, speech, music, sound effects). Provide detailed, structured summaries."
)

VIDEO_SUMMARY_PROMPT = (
    "Please analyze this short-form video and provide a structured summary with the following sections:\n\n"
    "**Topic / Theme:** What is this video about?\n"
    "**What Happens:** A clear description of the key events, actions, or content shown.\n"
    "**Audio & Speech:** What is said or heard? Mark down ALL dialogue and speech being said by anyone in the video, including every word spoken, and all music, sounds, sound effects, narration, voiceovers, etc.\n"
    "**Tone & Style:** What is the mood, energy, or style of the video?\n"
    "**Key Takeaway:** What is the main message, point, or purpose of this video?\n"
    "**Suggested Tags / Keywords:** A comma-separated list of 8-12 relevant search keywords.\n\n"
    "Be specific and descriptive."
)


def _detect_device() -> str:
    """Pick the best available device — MPS on Apple Silicon, else CPU."""
    if torch.backends.mps.is_available():
        logger.info("MPS (Apple Silicon) is available")
        return "mps"
    logger.warning("MPS not available, falling back to CPU")
    return "cpu"


def load_model() -> tuple[bool, str]:
    """
    Load the Qwen2.5-Omni-7B model into memory.

    Returns (success: bool, message: str).
    Should be called once at app startup in a background thread.
    """
    global _model, _processor, _model_load_error

    try:
        from transformers import (
            Qwen2_5OmniForConditionalGeneration,
            Qwen2_5OmniProcessor,
            QuantoConfig,
        )
    except ImportError as e:
        msg = (
            f"Could not import Qwen2.5-Omni classes: {e}. "
            "Make sure you installed transformers from the correct branch: "
            "pip install git+https://github.com/huggingface/transformers@v4.51.3-Qwen2.5-Omni-preview"
        )
        _model_load_error = msg
        logger.error(msg)
        return False, msg

    if _model is not None:
        return True, "Model already loaded"

    target_device = _detect_device()

    logger.info(f"Loading processor from {MODEL_ID}...")
    try:
        _processor = Qwen2_5OmniProcessor.from_pretrained(MODEL_ID)
    except Exception as e:
        _model_load_error = f"Failed to load processor: {e}"
        logger.error(_model_load_error)
        return False, _model_load_error

    # ── Strategy for Apple Silicon 16 GB ─────────────────────────────────────
    # Loading with device_map="mps" causes Metal to allocate one giant
    # contiguous buffer for all checkpoint shards (~20 GB), which exceeds
    # Metal's per-allocation limit → "Invalid buffer size" crash.
    #
    # Fix: load entirely onto CPU with low_cpu_mem_usage=True (streams each
    # shard individually), disable the Talker immediately to free ~2 GB,
    # then move the slimmed model to MPS as many smaller tensors.
    # If MPS move also fails (very low free RAM), fall back to CPU-only.
    # ─────────────────────────────────────────────────────────────────────────
    logger.info(f"Loading model from {MODEL_ID} onto CPU first (low_cpu_mem_usage=True)...")
    logger.info("This will download ~14 GB on first run — please be patient.")

    try:
        # 1. Define the 4-bit quantization configuration
        quantization_config = QuantoConfig(weights="int4")

        _model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16,
            quantization_config=quantization_config,
            device_map="cpu",           # avoid Metal single-buffer OOM during load
            low_cpu_mem_usage=True,     # stream shards one at a time
            attn_implementation="sdpa", # SDPA works on both CPU and MPS
        )

        # Disable the Talker (audio output head) — frees ~2 GB before MPS move.
        _model.disable_talker()
        logger.info("Talker (audio output head) disabled — text-only mode active")
        _model.eval()

        # Attempt to move to MPS so inference benefits from Apple Silicon GPU.
        # If it fails (OOM on 16 GB), we explicitly consolidate ALL params back
        # to CPU — a partial .to("mps") leaves the model in a split-device state
        # where some layers are on MPS and some on CPU, causing inference to crash.
        if target_device == "mps":
            logger.info("Attempting to move model to MPS (Apple Silicon GPU)...")
            try:
                _model = _model.to("mps")
                logger.info("Model successfully moved to MPS!")
            except Exception as mps_err:
                logger.warning(
                    f"Could not move model to MPS ({mps_err}). "
                    "Consolidating all parameters back to CPU for clean inference."
                )
                # Force every tensor back to CPU — this is critical.
                # After a failed .to("mps"), some layers may already be on MPS.
                _model = _model.to("cpu")
                torch.mps.empty_cache()
                gc.collect()
                logger.info("All model parameters on CPU — ready for CPU inference.")
        else:
            logger.info("MPS not available — running on CPU.")

        logger.info("Model loaded and ready!")
        return True, "Model loaded successfully"

    except Exception as e:
        _model_load_error = f"Failed to load model: {e}"
        _model = None
        gc.collect()
        logger.error(_model_load_error)
        return False, _model_load_error


def is_model_ready() -> bool:
    return _model is not None and _processor is not None


def get_load_error():
    return _model_load_error


def _patch_torchvision_io() -> None:
    """
    Restore torchvision.io.read_video which was removed in torchvision >= 0.21.
    qwen_omni_utils.v2_5.vision_process still calls torchvision.io.read_video;
    we re-implement it using PyAV (av), which is already installed as a
    transitive dependency of qwen-omni-utils.

    This patch is idempotent — if read_video already exists, it does nothing.
    """
    try:
        import torchvision.io as _tvio
        if hasattr(_tvio, "read_video"):
            return  # already present — nothing to do
    except ImportError:
        return  # torchvision not installed — leave it alone

    try:
        import av as _av
        import numpy as _np

        def _read_video_av(
            filename,
            start_pts=0,
            end_pts=None,
            pts_unit="pts",
            output_format="THWC",
        ):
            """
            Drop-in replacement for torchvision.io.read_video using PyAV.
            Returns (video_tensor [T,H,W,C or T,C,H,W], audio_tensor, info_dict).
            """
            container = _av.open(str(filename))

            # video metadata
            v_stream = container.streams.video[0]
            fps = float(v_stream.average_rate) if v_stream.average_rate else 30.0
            time_base = float(v_stream.time_base) if v_stream.time_base else 1 / fps

            # Convert pts_unit / start_end to seconds for seeking
            start_sec = 0.0
            end_sec = None
            if start_pts:
                start_sec = start_pts if pts_unit == "sec" else start_pts * time_base
            if end_pts is not None:
                end_sec = end_pts if pts_unit == "sec" else end_pts * time_base

            if start_sec:
                container.seek(int(start_sec / time_base), stream=v_stream)

            frames = []
            for frame in container.decode(video=0):
                t = frame.pts * time_base if frame.pts is not None else 0.0
                if end_sec is not None and t > end_sec:
                    break
                frames.append(frame.to_ndarray(format="rgb24"))

            container.close()

            if frames:
                video = torch.from_numpy(_np.stack(frames))  # T, H, W, C (uint8)
            else:
                video = torch.zeros((0, 1, 1, 3), dtype=torch.uint8)

            if output_format == "TCHW":
                video = video.permute(0, 3, 1, 2)

            audio = torch.zeros((0,), dtype=torch.float32)
            info = {"video_fps": fps, "audio_fps": 0}
            return video, audio, info

        _tvio.read_video = _read_video_av
        logger.info(
            "Patched torchvision.io.read_video with PyAV shim "
            "(torchvision >= 0.21 removed this API)."
        )

    except Exception as e:
        logger.warning(f"Could not install torchvision.io.read_video shim: {e}")


def summarize_video(video_path: str) -> dict:
    """
    Analyze a local .mp4 file with Qwen2.5-Omni-7B and return a summary.

    Args:
        video_path: Absolute path to the .mp4 file.

    Returns:
        dict with keys:
            success (bool)
            summary (str) — the model's text output
            error (str | None)
    """
    if not is_model_ready():
        err = _model_load_error or "Model is not loaded yet"
        return {"success": False, "summary": None, "error": err}

    if not Path(video_path).exists():
        return {"success": False, "summary": None, "error": f"File not found: {video_path}"}

    # Patch torchvision.io before qwen_omni_utils is imported — the utils
    # module calls read_video at import time when processing a video.
    _patch_torchvision_io()

    try:
        from qwen_omni_utils import process_mm_info
    except ImportError as e:
        return {
            "success": False,
            "summary": None,
            "error": (
                f"qwen-omni-utils not installed: {e}. "
                "Run: pip install qwen-omni-utils"
            ),
        }

    logger.info(f"Starting inference on: {video_path}")

    # Build the conversation with the video file path.
    # qwen-omni-utils handles frame extraction + audio extraction with
    # TMRoPE-aligned timestamps internally — we pass the raw .mp4 path.
    conversation = [
        {
            "role": "system",
            "content": [{"type": "text", "text": SYSTEM_PROMPT}],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "video", 
                    "video": video_path,
                    # ── Memory optimizations for 16 GB Mac ──
                    # Limit to 8 frames total to prevent attention matrix explosion
                    "max_frames": 8,
                    # Limit pixels per frame to 128 tokens (128 * 14 * 14 * 4) 
                    "max_pixels": 100352 
                },
                {"type": "text", "text": VIDEO_SUMMARY_PROMPT},
            ],
        },
    ]

    try:
        # process_mm_info handles TMRoPE-aligned extraction of:
        # - video frames (with absolute timestamps)
        # - audio waveform (with matching absolute timestamps)
        # use_audio_in_video=True is key — it processes audio + video together
        USE_AUDIO_IN_VIDEO = True

        logger.info("Extracting and processing multimodal content from video...")
        text_input = _processor.apply_chat_template(
            conversation, add_generation_prompt=True, tokenize=False
        )
        audios, images, videos = process_mm_info(
            conversation, use_audio_in_video=USE_AUDIO_IN_VIDEO
        )

        inputs = _processor(
            text=text_input,
            audio=audios,
            images=images,
            videos=videos,
            return_tensors="pt",
            padding=True,
            use_audio_in_video=USE_AUDIO_IN_VIDEO,
        )
        # Move inputs to the model's device; only cast float tensors to model dtype.
        # Casting integer tensors (input_ids, attention_mask) to float16 would break them.
        device = _model.device
        inputs = {
            k: (v.to(device).to(_model.dtype) if v.dtype.is_floating_point else v.to(device))
            for k, v in inputs.items()
        }

        logger.info("Running model inference (this may take a few minutes on 16 GB RAM)...")
        with torch.no_grad():
            # return_audio=False because we called model.disable_talker()
            text_ids = _model.generate(
                **inputs,
                use_audio_in_video=USE_AUDIO_IN_VIDEO,
                return_audio=False,
                max_new_tokens=1024,
            )

        # Decode only the newly generated tokens (not the input prompt)
        generated_ids = text_ids[:, inputs["input_ids"].shape[1]:]
        summary = _processor.batch_decode(
            generated_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0].strip()

        logger.info("Inference complete!")
        return {"success": True, "summary": summary, "error": None}

    except MemoryError as e:
        msg = (
            "Out of memory during inference. Your Mac has 16 GB of unified memory, "
            "which is below the recommended 32 GB for this model. "
            "Try closing other applications and uploading a shorter video."
        )
        logger.error(f"MemoryError: {e}")
        gc.collect()
        return {"success": False, "summary": None, "error": msg}
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            msg = (
                "Out of memory during inference. Your Mac has 16 GB of unified memory, "
                "which is below the recommended 32 GB for this model. "
                "Try closing other applications and uploading a shorter video."
            )
            gc.collect()
        else:
            msg = f"Runtime error during inference: {e}"
        logger.error(f"RuntimeError: {e}")
        return {"success": False, "summary": None, "error": msg}
    except Exception as e:
        msg = f"Unexpected error during inference: {e}"
        logger.error(msg, exc_info=True)
        return {"success": False, "summary": None, "error": msg}
    finally:
        # Clean up input tensors from device memory
        if "inputs" in dir():
            del inputs
        gc.collect()
