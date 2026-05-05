from elasticsearch import Elasticsearch
client = Elasticsearch("http://localhost:9200")
try:
    print(client.ml.put_trained_model(model_id=".elser_model_2", input={"field_names": ["text_field"]}))
except Exception as e:
    print(e)
try:
    print(client.ml.start_trained_model_deployment(model_id=".elser_model_2", wait_for="starting"))
except Exception as e:
    print(e)
