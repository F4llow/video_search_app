import os
import shutil
import uuid
import queue
import threading
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

import model
from s3_client import upload_video_to_b2, get_presigned_url

load_dotenv()

app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
es = Elasticsearch(es_url)

# Ensure uploads dir exists for temporary storage before processing
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Track processing status
processing_jobs = {}
job_results = {}
job_queue = queue.Queue()

def worker():
    while True:
        task = job_queue.get()
        if task is None:
            break
        file_path, filename, public_url = task
        
        if processing_jobs.get(filename) == "cancelled":
            print(f"Skipping cancelled job: {filename}")
            job_queue.task_done()
            continue
            
        processing_jobs[filename] = "processing"
        process_video(file_path, filename, public_url)
        job_queue.task_done()

threading.Thread(target=worker, daemon=True).start()

# Load model on startup
embedder = None
@app.on_event("startup")
def startup_event():
    global embedder
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    # Load model in a background thread or synchronously
    success, msg = model.load_model()
    if not success:
        print(f"Error loading model: {msg}")

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    # Create unique filename
    ext = os.path.splitext(file.filename)[1]
    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # Save temp file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Upload to Backblaze
    public_url = upload_video_to_b2(file_path, filename)
    
    # Mark as queued
    processing_jobs[filename] = "queued"

    # Add background task for processing
    job_queue.put((file_path, filename, public_url))

    video_url = f"http://localhost:8000/video/{filename}"
    return {"message": "Upload successful, processing started.", "url": video_url, "id": unique_id, "filename": filename}

@app.get("/video/{filename}")
async def get_video(filename: str):
    """Generate a presigned URL for a private B2 video and redirect the player to it."""
    url = get_presigned_url(filename)
    return RedirectResponse(url)

@app.get("/video_url/{filename}")
async def get_video_url_api(filename: str):
    """Return the presigned URL directly to avoid browser 307 redirect bugs for video players."""
    url = get_presigned_url(filename)
    return {"url": url}

@app.get("/status/{filename}")
async def get_status(filename: str):
    """Return the current processing status of the video."""
    return {
        "status": processing_jobs.get(filename, "unknown"),
        "summary": job_results.get(filename, "")
    }

@app.post("/cancel/{filename}")
async def cancel_job(filename: str):
    processing_jobs[filename] = "cancelled"
    return {"status": "cancelled"}

def process_video(file_path: str, filename: str, public_url: str):
    print(f"Processing video: {filename}")
    try:
        # Run inference
        result = model.summarize_video(file_path)
        if not result["success"]:
            print(f"Model failed: {result['error']}")
            processing_jobs[filename] = "failed"
            return
            
        if processing_jobs.get(filename) == "cancelled":
            print(f"Job {filename} cancelled mid-processing. Discarding summary.")
            return

        summary = result["summary"]
        job_results[filename] = summary
        
        vector = embedder.encode(summary).tolist()

        # Index to Elasticsearch
        try:
            es.index(
                index="videos",
                document={
                    "filename": filename,
                    "video_url": public_url,
                    "summary": summary,
                    "dense_embedding": vector
                }
            )
        except Exception as es_err:
            print(f"Warning: Indexing failed ({es_err}).")
            
        print(f"Successfully processed and indexed: {filename}")
        processing_jobs[filename] = "completed"
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in process_video: {e}")
        processing_jobs[filename] = "failed"
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)

@app.get("/search")
async def search_videos(q: str, mode: str = "semantic"):
    if not q:
        return {"results": []}

    try:
        if mode == "bm25":
            body = {
                "query": {
                    "match": {
                        "summary": q
                    }
                },
                "_source": ["filename", "video_url", "summary"]
            }
        else:
            # Semantic search using dense_embedding
            query_vector = embedder.encode(q).tolist()
            body = {
                "knn": {
                    "field": "dense_embedding",
                    "query_vector": query_vector,
                    "k": 10,
                    "num_candidates": 100
                },
                "_source": ["filename", "video_url", "summary"]
            }

        res = es.search(index="videos", body=body)
        hits = res['hits']['hits']
        results = [
            {
                "score": hit['_score'],
                "filename": hit['_source']['filename'],
                "url": f"http://localhost:8000/video/{hit['_source']['filename']}",
                "summary": hit['_source']['summary']
            }
            for hit in hits
        ]
        return {"results": results}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")
