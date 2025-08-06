import os
import gzip
import hashlib
import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient

BLOB_CONN_STR = os.getenv("BLOB_CONN_STR")
BLOB_CONTAINER = os.getenv("BLOB_CONTAINER_NAME")

def calculate_sha256(data_bytes):
    sha = hashlib.sha256()
    sha.update(data_bytes)
    return sha.hexdigest()

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = mytimer.schedule_status.last
    logging.info(f"Integrity check function started at {utc_timestamp}")

    blob_service = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
    blob_container = blob_service.get_container_client(BLOB_CONTAINER)

    for blob in blob_container.list_blobs():
        if not blob.name.endswith(".json.gz"):
            continue

        blob_client = blob_container.get_blob_client(blob.name)
        props = blob_client.get_blob_properties()
        expected_hash = props.metadata.get("sha256")

        if not expected_hash:
            logging.warning(f"No checksum metadata found for {blob.name}, skipping")
            continue

        compressed_data = blob_client.download_blob().readall()
        decompressed_data = gzip.decompress(compressed_data)
        actual_hash = calculate_sha256(decompressed_data)

        if actual_hash != expected_hash:
            logging.error(f"Checksum mismatch for {blob.name}! Possible corruption.")
        else:
            logging.info(f"Verified: {blob.name}")

    logging.info("Integrity check completed.")
