import os
import gzip
import hashlib
import argparse
from azure.storage.blob import BlobServiceClient

BLOB_CONN_STR = os.getenv("BLOB_CONN_STR")
BLOB_CONTAINER = os.getenv("BLOB_CONTAINER_NAME")

def calculate_sha256(data_bytes):
    sha = hashlib.sha256()
    sha.update(data_bytes)
    return sha.hexdigest()

def verify(record_id=None):
    blob_service = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
    blob_container = blob_service.get_container_client(BLOB_CONTAINER)

    for blob in blob_container.list_blobs():
        if not blob.name.endswith(".json.gz"):
            continue

        if record_id and not blob.name.startswith(record_id):
            continue

        blob_client = blob_container.get_blob_client(blob.name)
        props = blob_client.get_blob_properties()
        expected_hash = props.metadata.get("sha256")

        compressed_data = blob_client.download_blob().readall()
        actual_hash = calculate_sha256(gzip.decompress(compressed_data))

        if expected_hash and expected_hash == actual_hash:
            print(f"✅ Verified: {blob.name}")
        else:
            print(f"❌ Mismatch: {blob.name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify checksum of archived records")
    parser.add_argument("--id", help="Optional record ID to verify (verifies all if omitted)")
    args = parser.parse_args()

    verify(args.id)
