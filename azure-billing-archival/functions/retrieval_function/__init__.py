import os
import json
import gzip
import logging
import azure.functions as func
from azure.cosmos import CosmosClient, exceptions
from azure.storage.blob import BlobServiceClient

# Env vars
COSMOS_URL = os.getenv("COSMOS_URL")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = os.getenv("COSMOS_DB_NAME")
CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME")

BLOB_CONN_STR = os.getenv("BLOB_CONN_STR")
BLOB_CONTAINER = os.getenv("BLOB_CONTAINER_NAME")

def main(req: func.HttpRequest) -> func.HttpResponse:
    record_id = req.params.get('id')
    if not record_id:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            record_id = req_body.get('id')

    if not record_id:
        return func.HttpResponse(
            json.dumps({"error": "Missing 'id' parameter"}),
            status_code=400,
            mimetype="application/json"
        )

    try:
        # First try Cosmos DB
        cosmos_client = CosmosClient(COSMOS_URL, COSMOS_KEY)
        db = cosmos_client.get_database_client(DATABASE_NAME)
        container = db.get_container_client(CONTAINER_NAME)

        query = f"SELECT * FROM c WHERE c.id = '{record_id}'"
        items = list(container.query_items(query, enable_cross_partition_query=True))

        if items:
            logging.info(f"Record {record_id} found in hot tier")
            return func.HttpResponse(
                json.dumps(items[0]),
                status_code=200,
                mimetype="application/json"
            )

        # If not found, try Blob Storage
        logging.info(f"Record {record_id} not found in hot tier, checking cold tier")
        blob_service = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
        blob_container = blob_service.get_container_client(BLOB_CONTAINER)
        blob_name = f"{record_id}.json.gz"

        blob_client = blob_container.get_blob_client(blob_name)
        blob_data = blob_client.download_blob().readall()
        decompressed_data = gzip.decompress(blob_data)
        record = json.loads(decompressed_data.decode("utf-8"))

        logging.info(f"Record {record_id} retrieved from cold tier")
        return func.HttpResponse(
            json.dumps(record),
            status_code=200,
            mimetype="application/json"
        )

    except exceptions.CosmosHttpResponseError as e:
        logging.error(f"Cosmos DB error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal database error"}),
            status_code=500,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )
