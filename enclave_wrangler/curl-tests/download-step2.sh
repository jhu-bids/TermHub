#!/bin/bash
source ../../env/.env
curl https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/views2/ri.foundry.main.transaction.00000018-7b1d-bb28-aed1-885fe335491c/files?pageSize=100 -H "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN" | json_pp

