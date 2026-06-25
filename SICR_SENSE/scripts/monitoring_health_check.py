"""
Simple health-check script for monitoring endpoints.
Run with the dev server running (uvicorn) and an active session cookie if needed.
"""
try:
    import requests
except Exception:
    requests = None
from urllib.parse import urljoin
import json

BASE = 'http://localhost:8000'
ENDPOINTS = [
    '/api/v1/monitoring/overview',
    '/api/v1/monitoring/performance',
    '/api/v1/monitoring/predictions',
    '/api/v1/monitoring/risk',
    '/api/v1/monitoring/resources',
    '/api/v1/monitoring/audit-logs'
]

s = requests.Session() if requests else None
# If your dev server uses cookie auth, ensure cookies are present in the session.

for ep in ENDPOINTS:
    url = urljoin(BASE, ep)
    try:
        if requests:
            r = s.get(url, timeout=5)
            print(f"{ep}: {r.status_code}")
            try:
                print('  JSON keys:', list(r.json().keys()) if r.headers.get('content-type','').startswith('application/json') else 'not-json')
            except Exception as e:
                print('  JSON parse failed:', e)
        else:
            # Fallback to urllib
            from urllib.request import urlopen, Request
            req = Request(url)
            with urlopen(req, timeout=5) as resp:
                status = resp.getcode()
                content_type = resp.headers.get('Content-Type','')
                print(f"{ep}: {status}")
                if content_type.startswith('application/json'):
                    body = resp.read().decode('utf-8')
                    try:
                        j = json.loads(body)
                        print('  JSON keys:', list(j.keys()))
                    except Exception as e:
                        print('  JSON parse failed:', e)
    except Exception as e:
        print(f"{ep}: ERROR - {e}")

print('\nHealth check complete. WebSocket connectivity requires a browser session or dedicated websocket client.')
