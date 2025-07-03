import os
import json

credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if credentials_json:
    with open("/app/credentials.json", "w") as f:
        json.dump(json.loads(credentials_json), f)
    print("Google credentials created from environment variable")
else:
    print("GOOGLE_CREDENTIALS_JSON not set")