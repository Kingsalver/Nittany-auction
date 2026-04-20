import urllib.request
import json

# Login First
req_login = urllib.request.Request(
    "http://127.0.0.1:8000/api/login",
    data=b"username=arubertelli0%40lsu.edu&password=default123",
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

try:
    with urllib.request.urlopen(req_login) as response:
        login_data = json.loads(response.read())
        token = login_data["access_token"]
except Exception as e:
    print(f"Login failed: {e}")
    exit(1)

# Now Test POST /api/requests
data = json.dumps({"request_type": "BecomeASeller", "request_desc": "Hello"}).encode("utf-8")
req_post = urllib.request.Request(
    "http://127.0.0.1:8000/api/requests",
    data=data,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
)

try:
    with urllib.request.urlopen(req_post) as response:
        print(response.read())
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    print(e.read().decode())
