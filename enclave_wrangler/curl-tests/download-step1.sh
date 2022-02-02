#!/bin/bash
source ../../env/.env
# curl https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/transactions/master -H "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN" | json_pp
curl https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.47a26e85-307e-4a21-9583-f58c90b73455/transactions/master -H "authorization: Bearer $OTHER_TOKEN" | json_pp

