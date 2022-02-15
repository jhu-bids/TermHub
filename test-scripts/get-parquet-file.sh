#!/bin/bash
source ./env/.env

echo "this isn't working...not sure why. I think I had it working at some point?"

curl -XGET 'https://unite.nih.gov/foundry-data-proxy/api/web/dataproxy/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/transactions/ri.foundry.main.transaction.00000023-7ef5-1149-a75c-5a6342aacad6/spark%2Fpart-00000-c94edb9f-1221-4ae8-ba74-58848a4d79cb-c000.snappy.parquet' -H 'authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN'  -OJ
