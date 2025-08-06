# Azure Billing Records Hot/Cold Storage Optimization

## Overview

This project implements a **cost-optimized serverless architecture** for managing billing records in Azure:

-   **Hot tier (Cosmos DB)** → Stores recent 90 days of records for fast reads.
-   **Cold tier (Azure Blob Storage)** → Stores older records in compressed format with checksums.
-   **Serverless Functions** → Automate archival, retrieval, and integrity validation.
-   **Disaster Recovery (DR)** → Restore data from cold tier if needed.

---

## Architecture

![Architecture Diagram](diagrams/architecture.png)

**Flow:**

1. **Archival Function** runs daily → Moves old records (>90 days) to Blob Storage.
2. **Retrieval Function** → Checks Cosmos DB first, then Blob Storage if not found.
3. **Integrity Check Function** runs weekly → Validates archived files using SHA256 checksums.
4. **DR Scripts** → Restore archived data into Cosmos DB on demand.

---

## Components

### Azure Functions

1. **Archival Function**

    - Trigger: Timer (daily 2 AM UTC)
    - Moves old data to Blob Storage
    - Compresses data
    - Stores SHA256 checksum in blob metadata
    - Deletes from Cosmos DB after verification

2. **Retrieval Function**

    - Trigger: HTTP (GET or POST)
    - Reads from Cosmos DB first
    - Falls back to Blob Storage if record not found
    - Decompresses before returning

3. **Integrity Check Function**
    - Trigger: Timer (weekly, Sunday 3 AM UTC)
    - Recalculates checksum of each archived blob
    - Logs mismatches for investigation

---

## Deployment

### 1. Provision Infrastructure

```bash
az deployment group create \
  --resource-group <your-rg-name> \
  --template-file infra/main.bicep \
  --parameters projectName=mybillingapp location=westeurope
```

---

## Reference

> Please refer to this link: [Chatgpt Link](https://chatgpt.com/share/68938543-6a70-8002-88d2-6c9f1baddaad)
