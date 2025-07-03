#!/bin/bash

set -e

if [[ -n "$GOOGLE_CREDENTIALS_JSON" ]]; then
  echo "$GOOGLE_CREDENTIALS_JSON" \
    | base64 -d \
    > /app/credentials.json
  echo "Google credentials created from GOOGLE_CREDENTIALS_JSON"
else
  echo "GOOGLE_CREDENTIALS_JSON not provided; skipping credentials.json"
fi



# Start backend
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 