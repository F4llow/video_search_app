# CLAUDE.md
This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Video Search App - A multimodal video analysis and semantic search platform. Users upload videos which are analyzed by Qwen2.5-Omni-7B to generate AI summaries, then indexed in Elasticsearch for semantic search.

## Commands

**Backend (FastAPI)**
- Install: `pip install -r backend/requirements.txt`
- Start: `uvicorn backend.main:app --reload` (port 8000)
- Setup Elasticsearch: `python backend/es_setup.py`
- Backfill embeddings: `python backend/backfill_embeddings.py`

**Frontend (React + Vite)**
- Install: `cd frontend && npm install`
- Dev server: `npm run dev` (port 5173)
- Build: `npm run build`
- Lint: `npm run lint`

**Infrastructure**
- Start Elasticsearch + Kibana: `docker-compose up -d`

## Architecture

**Backend (`backend/`)**
- `main.py` - FastAPI server with video upload, status polling, and search endpoints
- `model.py` - Qwen2.5-Omni-7B inference with TMRoPE-aligned audio+video processing; runs on MPS (Apple Silicon) or CPU
- `es_setup.py` - Initializes Elasticsearch index with ELSER sparse vector pipeline
- `backfill_embeddings.py` - Adds dense vectors (all-MiniLM-L6-v2, 384-dim) to existing documents
- `s3_client.py` - B2 cloud storage upload/presigned URLs via S3-compatible API

Key flows:
1. Video upload → B2 storage → queued for processing
2. Background worker → Qwen2.5-Omni inference → summary → SentenceTransformer embedding → Elasticsearch
3. Search supports BM25 (keyword) and semantic (kNN on dense_embedding) modes

**Frontend (`frontend/`)**
- `App.jsx` - React Router setup with Analyze/Search pages
- `pages/AnalyzePage.jsx` - Video upload, processing status polling, AI summary display
- `pages/SearchPage.jsx` - Search bar with results and video player
- `components/` - Reusable SearchBar, SearchResults, VideoPlayer, VideoUploader

**Elasticsearch Schema**
- `summary` (text) - AI-generated video summary
- `summary_embedding` (sparse_vector) - ELSER embeddings
- `dense_embedding` (dense_vector, 384-dim) - all-MiniLM-L6-v2 for semantic search
- `filename`, `video_url` (keyword)

## Environment Variables

Backend requires in `.env`:
- `ELASTICSEARCH_URL` (default: http://localhost:9200)
- `B2_ENDPOINT_URL`, `B2_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_PUBLIC_URL_PREFIX`

## Model Details

Qwen2.5-Omni-7B (`Qwen/Qwen2.5-Omni-7B`):
- Loaded with 4-bit quantization (QuantoConfig `int4`)
- Text-only output (Talker disabled)
- Patches `torchvision.io.read_video` via PyAV (removed in torchvision >= 0.21)

SentenceTransformer: `all-MiniLM-L6-v2` for 384-dim dense embeddings
