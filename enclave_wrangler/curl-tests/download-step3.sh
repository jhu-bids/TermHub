#!/bin/bash
source ../../env/.env
curl https://unite.nih.gov/foundry-data-proxy/api/web/dataproxy/datasets/ri.foundry.main.dataset.b5bcc7e3-e3cb-4fd7-88ae-0f1e193ed789/transactions/ri.foundry.main.transaction.00000015-d68c-a198-a670-19931c315f24/spark%2Fpart-00001-fbaa3ebf-3ca2-4781-adc2-64c382ec8271-c000.csv -H "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN"

