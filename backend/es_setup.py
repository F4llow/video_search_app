import time
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os

load_dotenv()
es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
client = Elasticsearch(es_url)

def wait_for_es():
    for _ in range(60):
        try:
            if client.ping():
                print("Elasticsearch is up.")
                return True
        except:
            pass
        time.sleep(2)
    return False

def setup():
    if not wait_for_es():
        print("ES not reachable")
        return
    
    print("Ensuring ELSER model is deployed...")
    try:
        # This will download and start the model deployment automatically in 8.11+
        res = client.ml.start_trained_model_deployment(model_id=".elser_model_2", wait_for="started", timeout="2m")
        print("ELSER model started.", res)
    except Exception as e:
        print("ELSER model start message:", e)

    print("Creating ingest pipeline...")
    try:
        client.ingest.put_pipeline(
            id="elser-v2-pipeline",
            body={
                "processors": [
                    {
                        "inference": {
                            "model_id": ".elser_model_2",
                            "input_output": [
                                {
                                    "input_field": "summary",
                                    "output_field": "summary_embedding"
                                }
                            ]
                        }
                    }
                ]
            }
        )
        print("Ingest pipeline created.")
    except Exception as e:
        print("Pipeline creation error:", e)

    print("Creating index mapping...")
    try:
        client.indices.create(
            index="videos",
            body={
                "settings": {
                    "default_pipeline": "elser-v2-pipeline"
                },
                "mappings": {
                    "properties": {
                        "summary": {"type": "text"},
                        "summary_embedding": {"type": "sparse_vector"},
                        "filename": {"type": "keyword"},
                        "video_url": {"type": "keyword"}
                    }
                }
            },
            ignore=400
        )
        print("Index mapped successfully.")
    except Exception as e:
        print("Index mapping error:", e)

if __name__ == "__main__":
    setup()
