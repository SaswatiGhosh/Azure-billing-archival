import os
import json
import gzip
import datetime
import hashlib
import logging
import azure.functions as func
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient

# Env vars (set in Azure Function App config)
COSMOS_URL = os.getenv("COSMOS_URL")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = os.getenv("COSMOS_DB_NAME")
CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME")

BLOB_CONN_STR = os.getenv("BLOB_CONN_STR")
BLOB_CONTAINER = os.getenv("BLOB_CONTAINER_NAME")

CUTOFF_DAYS = int(os.getenv("ARCHIVAL_CUTOFF_DAYS", "90"))

def calculate_sha256(data_bytes):
    sha = hashlib.sha256()
    sha.update(data_bytes)
    return sha.hexdigest()

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    logging.info(f"Archival function started at {utc_timestamp}")

    cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=CUTOFF_DAYS)).isoformat()

    cosmos_client = CosmosClient(COSMOS_URL, COSMOS_KEY)
    db = cosmos_client.get_database_client(DATABASE_NAME)
    container = db.get_container_client(CONTAINER_NAME)

    blob_service = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
    blob_container = blob_service.get_container_client(BLOB_CONTAINER)

    query = f"SELECT * FROM c WHERE c.timestamp < '{cutoff_date}'"
    old_records = container.query_items(query, enable_cross_partition_query=True)

    for record in old_records:
        record_id = record["id"]
        partition_key = record["partitionKey"]

        # Convert record to bytes
        record_bytes = json.dumps(record).encode("utf-8")

        # Calculate checksum
        checksum = calculate_sha256(record_bytes)

        # Compress
        compressed_data = gzip.compress(record_bytes)

        # Upload to Blob with checksum metadata
        blob_name = f"{record_id}.json.gz"
        blob_container.upload_blob(
            blob_name,
            compressed_data,
            overwrite=True,
            metadata={"sha256": checksum}
        )

        # Verify checksum before deletion
        downloaded_blob = blob_container.get_blob_client(blob_name).download_blob().readall()
        if calculate_sha256(gzip.decompress(downloaded_blob)) == checksum:
            container.delete_item(record_id, partition_key=partition_key)
            logging.info(f"Archived and deleted record {record_id}")
        else:
            logging.error(f"Checksum mismatch for {record_id}, skipping deletion")

    logging.info("Archival function completed.")
