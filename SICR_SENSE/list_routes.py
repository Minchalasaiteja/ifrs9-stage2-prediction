from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("Registered Routes:")
for route in app.routes:
    methods = getattr(route, "methods", None)
    if methods:
        print(f"{list(methods)} {route.path}")
