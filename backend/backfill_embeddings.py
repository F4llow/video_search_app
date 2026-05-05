import os
import time
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()
es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
client = Elasticsearch(es_url)

print("Loading SentenceTransformer model...")
# all-MiniLM-L6-v2 produces 384-dimensional dense vectors
model = SentenceTransformer('all-MiniLM-L6-v2')

print("Removing default ELSER pipeline from index settings...")
try:
    client.indices.put_settings(
        index="videos",
        body={"index": {"default_pipeline": "_none"}}
    )
    print("Settings updated successfully.")
except Exception as e:
    print("Settings update error:", e)

print("Updating index mapping to include dense_embedding...")
try:
    client.indices.put_mapping(
        index="videos",
        body={
            "properties": {
                "dense_embedding": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine"
                }
            }
        }
    )
    print("Mapping updated successfully.")
except Exception as e:
    print("Mapping update error:", e)

print("Fetching existing videos to backfill...")
# We use scroll or just search since there are only 11 documents
res = client.search(index="videos", body={"query": {"match_all": {}}}, size=100)
hits = res['hits']['hits']
print(f"Found {len(hits)} videos.")

for hit in hits:
    doc_id = hit['_id']
    summary = hit['_source'].get('summary', '')
    if summary:
        print(f"Generating embedding for doc {doc_id}...")
        vector = model.encode(summary).tolist()
        
        # Update the document
        client.update(
            index="videos",
            id=doc_id,
            body={
                "doc": {
                    "dense_embedding": vector
                }
            }
        )
        print(f"Updated doc {doc_id}.")
print("Backfill complete!")
