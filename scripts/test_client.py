import os
import httpx

BASE = os.getenv("BASE", "http://127.0.0.1:8000")
API_KEY = os.getenv("API_KEY", "dev-key-1")

def main():
    # health
    print(httpx.get(f"{BASE}/health").json())

    # get token if auth enabled
    token_resp = httpx.post(
        f"{BASE}/auth/token",
        headers={"X-API-Key": API_KEY},
        json={"subject": "local-dev"},
        timeout=10,
    )
    if token_resp.status_code == 200:
        token = token_resp.json()["access_token"]
        print("token ok")
        headers={"Authorization": f"Bearer {token}"}
    else:
        print("token not issued:", token_resp.status_code, token_resp.text)
        headers={}

    # Call MCP over SSE / HTTP transport depends on client; this just shows headers are accepted at gateway.
    print("Done.")

if __name__ == "__main__":
    main()
