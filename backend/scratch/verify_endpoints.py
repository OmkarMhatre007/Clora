import urllib.request
import json

def test_endpoints():
    print("Testing Frontend HTTP Server...")
    r = urllib.request.urlopen("http://127.0.0.1:3000")
    print("Frontend status:", r.status)

    print("\nTesting Backend /api/models...")
    r2 = urllib.request.urlopen("http://127.0.0.1:8000/api/models")
    data = json.loads(r2.read().decode("utf-8"))
    print("Available Models:", data.get("available_models"))
    print("Active Model:", data.get("active_model"))

    print("\nTesting Backend /api/models/select (switch to qwen2.5:3b)...")
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/models/select",
        data=json.dumps({"model_name": "qwen2.5:3b"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    r3 = urllib.request.urlopen(req)
    data3 = json.loads(r3.read().decode("utf-8"))
    print("Select Response:", data3)

    print("\nTesting Backend /api/workspaces/default-workspace/files...")
    r4 = urllib.request.urlopen("http://127.0.0.1:8000/api/workspaces/default-workspace/files")
    data4 = json.loads(r4.read().decode("utf-8"))
    print(f"Files Count: {len(data4.get('items', []))}")

    print("\nAll Core Endpoints Operational!")

if __name__ == "__main__":
    test_endpoints()
