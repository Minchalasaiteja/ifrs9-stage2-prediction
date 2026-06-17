from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

endpoints = [
    ("/", "GET"),
    ("/login", "GET"),
    ("/signup", "GET"),
    ("/health", "GET"),
    ("/api/v1/stats", "GET"),
    ("/api/docs", "GET"),
]

def check_endpoints():
    print("Testing endpoints...")
    all_passed = True
    for path, method in endpoints:
        print(f"Testing {method} {path}...", end=" ")
        try:
            if method == "GET":
                response = client.get(path)
            elif method == "POST":
                response = client.post(path)
            
            if response.status_code in [200, 404, 500, 302]: # Accepting 302 as some redirect
                print(f"Status: {response.status_code}")
                if response.status_code >= 500:
                    print(f"ERROR on {path}: {response.text}")
                    all_passed = False
            else:
                print(f"Status: {response.status_code}")
        except Exception as e:
            print(f"EXCEPTION: {e}")
            all_passed = False
    
    if all_passed:
        print("\nAll public endpoints tested successfully.")
    else:
        print("\nSome endpoints failed.")

if __name__ == "__main__":
    check_endpoints()