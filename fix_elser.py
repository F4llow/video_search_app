from elasticsearch import Elasticsearch
client = Elasticsearch("http://localhost:9200")
try:
    print("Downloading ELSER...")
    res = client.perform_request("PUT", "/_ml/trained_models/.elser_model_2", body={"input": {"field_names": ["text_field"]}})
    print(res)
except Exception as e:
    print(e)
try:
    print("Starting deployment...")
    res = client.ml.start_trained_model_deployment(model_id=".elser_model_2", wait_for="started", timeout="2m")
    print(res)
except Exception as e:
    print(e)
