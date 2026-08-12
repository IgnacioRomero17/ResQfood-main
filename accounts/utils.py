import requests
from django.conf import settings

API_BASE = "http://127.0.0.1:8000"  # ajustá si usás otro host/puerto

def api_headers_from_session(session):
    access = session.get("jwt_access")
    return {"Authorization": f"Bearer {access}"} if access else {}

def api_get(session, path, **kwargs):
    headers = api_headers_from_session(session)
    headers.update(kwargs.pop("headers", {}))
    return requests.get(f"{API_BASE}{path}", headers=headers, timeout=8, **kwargs)

def api_post(session, path, json=None, **kwargs):
    headers = api_headers_from_session(session)
    headers.update(kwargs.pop("headers", {}))
    return requests.post(f"{API_BASE}{path}", headers=headers, json=json, timeout=8, **kwargs)
