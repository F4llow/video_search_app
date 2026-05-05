# Video Search App

A multimodal video analysis and semantic search platform powered by Qwen2.5-Omni-7B. Upload videos to receive AI-generated summaries, then search through your video library using natural language queries.

## Features

- **AI Video Analysis**: Automatic analysis of uploaded videos using Qwen2.5-Omni-7B with TMRoPE-aligned audio+video processing
- **Semantic Search**: Find videos using natural language queries with dense vector similarity (all-MiniLM-L6-v2, 384-dim)
- **Keyword Search**: Traditional BM25 full-text search as an alternative
- **Modern UI**: Clean, responsive React interface with real-time processing status updates
- **Cloud Storage**: B2 cloud storage integration with presigned URLs for video delivery

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Frontend   │────▶│  FastAPI (8000) │────▶│  Elasticsearch   │
│  (Vite)     │     │  - Video upload │     │  (9200, 5601)    │
│  Port 5173  │     │  - Qwen2.5-Omni │     │  - videos index  │
└─────────────┘     │  - Search API   │     └──────────────────┘
                    └─────────────────┘
                           │
                           ▼
                    ┌─────────────────┐
                    │  B2 Cloud       │
                    │  Storage        │
                    └─────────────────┘
```

## Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **Docker & Docker Compose** (for Elasticsearch + Kibana)
- **GPU**: Apple Silicon (MPS) for model inference
- **RAM**: 16 GB minimum (32 GB recommended for larger videos)

## Installation

### 1. Clone and Setup Backend

```bash
cd backend
pip install -r requirements.txt
```

### 2. Setup Frontend

```bash
cd frontend
npm install
```

### 3. Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200

# B2 Cloud Storage (Backblaze)
B2_ENDPOINT_URL=https://s3.us-west-001.backblazeb2.com
B2_KEY_ID=your_key_id
B2_APPLICATION_KEY=your_application_key
B2_BUCKET_NAME=your_bucket_name
B2_PUBLIC_URL_PREFIX=https://f001.backblazeb2.com/file/your_bucket_name
```

### 4. Start Infrastructure

```bash
docker-compose up -d
```

Wait for Elasticsearch to be ready, then initialize the index:

```bash
python backend/es_setup.py
```

## Running the Application

### Start Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Start Frontend Development Server

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Usage

### Analyze a Video

1. Navigate to the **Analyze** page
2. Upload a video file (MP4, WebM, etc.)
3. Click "Analyze Video" to start processing
4. Wait for the AI to generate a structured summary

### Search Videos

1. Navigate to the **Search** page
2. Enter a natural language query (e.g., "person explaining machine learning")
3. Choose search mode:
   - **Semantic**: Vector similarity search (default)
   - **Keyword (BM25)**: Full-text keyword search
4. Click a result to play the video

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload a video file |
| `/status/{filename}` | GET | Get processing status |
| `/cancel/{filename}` | POST | Cancel a processing job |
| `/search?q=query&mode=semantic` | GET | Search videos |
| `/video/{filename}` | GET | Get presigned video URL |
| `/video_url/{filename}` | GET | Get video URL directly |

## Elasticsearch Schema

| Field | Type | Description |
|-------|------|-------------|
| `summary` | text | AI-generated video summary |
| `summary_embedding` | sparse_vector | ELSER sparse embeddings |
| `dense_embedding` | dense_vector (384) | all-MiniLM-L6-v2 embeddings |
| `filename` | keyword | Unique video filename |
| `video_url` | keyword | B2 storage URL |

## Model Details

### Qwen2.5-Omni-7B
- **Base**: HuggingFace `Qwen/Qwen2.5-Omni-7B`
- **Quantization**: 4-bit (QuantoConfig `int4`)
- **Output**: Text-only (Talker disabled)
- **Video**: Max 8 frames, max_pixels=100352
- **Audio**: Enabled via TMRoPE pipeline

### SentenceTransformer
- **Model**: `all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Similarity**: Cosine

## Project Structure

```
video_search_app/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── model.py             # Qwen2.5-Omni inference
│   ├── es_setup.py          # Elasticsearch initialization
│   ├── backfill_embeddings.py  # Embedding backfill script
│   ├── s3_client.py         # B2 storage client
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main app with routing
│   │   ├── components/      # Reusable UI components
│   │   └── pages/           # AnalyzePage, SearchPage
│   └── package.json
├── docker-compose.yml       # Elasticsearch + Kibana
└── .env                     # Environment variables
```

## Troubleshooting

### Model Loading Issues
- Ensure you have the correct transformers branch: `pip install git+https://github.com/huggingface/transformers@v4.51.3-Qwen2.5-Omni-preview`
- Check available RAM (16 GB minimum)
- Close other applications if experiencing OOM errors

### Elasticsearch Connection
- Verify Docker containers are running: `docker-compose ps`
- Check Elasticsearch health: `curl http://localhost:9200/_cluster/health`

### Video Processing Fails
- Ensure video file is not corrupted
- Try shorter videos first (< 2 minutes recommended)
- Check B2 credentials if upload fails

## License

MIT
