import json
import sys

import requests



# Authentication parameters
auth_server_url = "https://des-sts-int.mbi.cloud.ihf/api/oauth/token/api/oauth/token"
client_id = "1f7e6552-7dc0-4df1-8150-74f94c8043ab"
client_secret = "554230a2-003b-4fd1-ace7-ce856723ab0f"

token_req_payload = {'grant_type': 'client_credentials'}

token_resp = requests.post(auth_server_url, data=token_req_payload, verify=False, allow_redirects=False, auth=(client_id, client_secret))

headers = {
  'Content-Type: application/x-www-form-urlencoded',
  'x-itau-correlationID: foundation',
  'x-itau-flowID: 47f5f458-7b7a-40bd-ae4f-df9c6ea141c2'
}

if token_resp.status_code !=200:
  print("Failed to obtain token from the OAuth 2.0 server", file=sys.stderr)
  sys.exit(1)
else:
  print("Successfuly obtained a new token")
  tokens = json.loads(token_resp.text)

print(tokens["access"])

