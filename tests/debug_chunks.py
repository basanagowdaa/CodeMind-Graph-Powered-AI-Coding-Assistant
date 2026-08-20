"""Debug: inspect raw HydraDB chunk structure to find where text content lives."""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from backend.hydra.client import HydraClient
from backend.hydra.ingestion import HydraIngestion

client = HydraClient(api_key=os.environ["HYDRA_DB_API_KEY"])
client.verify_connection()

test_db = f"codemind-debug-{int(time.time())}"
client.ensure_database(test_db)
print(f"Created test database: {test_db}")

ingestion = HydraIngestion(client)

entities = [
    {
        "id": "func:authenticate_user",
        "database": test_db,
        "collection": "default",
        "title": "Function: authenticate_user",
        "type": "codemind",
        "kind": "knowledge_base",
        "provider": "codemind",
        "external_id": "func:authenticate_user",
        "fields": {
            "kind": "knowledge_base",
            "title": "Function: authenticate_user",
            "body": "Function: authenticate_user\nFile: services/auth_service.py\nLine: 45\nAuthenticates a user and issues token pair.\nCalls: get_user_by_username, verify_password, create_access_token, create_refresh_token",
        },
        "metadata": {"entity_type": "Function", "file": "services/auth_service.py"},
    }
]

print("Ingesting entity...")
ingestion.ingest_code_graph(
    database=test_db,
    entities=entities,
    graph_payload={},
    wait_for_completion=True,
)

print("Waiting 10s for indexing...")
time.sleep(10)

print("Querying...")
raw = client.raw.query(
    database=test_db,
    query="authenticate_user",
    type="knowledge",
    query_by="hybrid",
    mode="thinking",
    graph_context=True,
    query_forceful_relations=True,
    max_results=5,
)

print(f"\nraw type: {type(raw)}")
if hasattr(raw, "data") and raw.data:
    data = raw.data
    print(f"data type: {type(data)}")

    if hasattr(data, "chunks") and data.chunks:
        for i, chunk in enumerate(data.chunks[:3]):
            print(f"\n--- Chunk {i} ---")
            print(f"  type: {type(chunk)}")
            attrs = [a for a in dir(chunk) if not a.startswith("_")]
            print(f"  attrs: {attrs}")
            for attr in attrs:
                val = getattr(chunk, attr, "N/A")
                if callable(val):
                    continue
                print(f"  {attr} = {repr(val)[:300]}")
    else:
        print("No chunks in data")
else:
    print("No data in response")

try:
    client.delete_database(test_db)
    print(f"Deleted test database: {test_db}")
except Exception:
    pass
