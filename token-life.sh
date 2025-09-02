#!/bin/bash

# Default format
FORMAT=${1:-"date-days"}

# Activate the virtual environment and run the token TTL check
source ./venv/bin/activate
python -c "from enclave_wrangler.utils import check_token_ttl; print(check_token_ttl(format='$FORMAT'))"
