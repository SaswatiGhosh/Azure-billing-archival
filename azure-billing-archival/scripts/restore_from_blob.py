import os
import json
import gzip
import argparse
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient

# Env vars
COSMOS_URL = os.getenv("COSMOS_URL")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = os.getenv("COSMOS_DB_NAME")
CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME")

BLOB_CONN_STR = os.getenv("BLOB_CONN_STR")
BLOB_CONTAINER = os.getenv("BLOB_CONTAINER_NAME")

def restore_all(record_id=None):
    cosmos_client = CosmosClient(COSMOS_URL, COSMOS_KEY)
    db = cosmos_client.get_database_client(DATABASE_NAME)
    container = db.get_container_client(CONTAINER_NAME)

    blob_service = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
    blob_container = blob_service.get_container_client(BLOB_CONTAINER)

    for blob in blob_container.list_blobs():
        if not blob.name.endswith(".json.gz"):
            continue

        if record_id and not blob.name.startswith(record_id):
            continue

        blob_client = blob_container.get_blob_client(blob.name)
        compressed_data = blob_client.download_blob().readall()
        record = json.loads(gzip.decompress(compressed_data).decode('utf-8'))

        container.upsert_item(record)
        print(f"Restored record: {record['id']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore archived records from Blob to Cosmos DB")
    parser.add_argument("--id", help="Optional record ID to restore (restores all if omitted)")
    args = parser.parse_args()

    restore_all(args.id)
