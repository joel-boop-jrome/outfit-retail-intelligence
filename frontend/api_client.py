"""
How the Streamlit dashboard talks to the backend.

If the FastAPI server is running (default http://127.0.0.1:8000, or set API_URL), requests go
over HTTP. If it is not, the very same functions in backend/services.py are called in-process,
so the dashboard always works with one command. `mode()` says which path is in use and is
shown in the page footer so nobody is misled.
"""
import os
import time
from typing import Dict, Optional

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
_state = {"checked": 0.0, "up": False}


def _server_up() -> bool:
    now = time.time()
    if now - _state["checked"] < 15:            # re-check at most every 15 seconds
        return _state["up"]
    _state["checked"] = now
    try:
        import requests
        _state["up"] = requests.get(f"{API_URL}/health", timeout=0.4).ok
    except Exception:
        _state["up"] = False
    return _state["up"]


def mode() -> str:
    return f"API server at {API_URL}" if _server_up() else "built-in (in-process) services"


def _http(method: str, path: str, **kw):
    import requests
    r = requests.request(method, f"{API_URL}{path}", timeout=5, **kw)
    r.raise_for_status()
    return r.json()


def get_stock_map() -> Dict[str, float]:
    if _server_up():
        try:
            return {p["sku"]: p["current_stock"] for p in _http("GET", "/products") if p["current_stock"] is not None}
        except Exception:
            pass
    from backend import services
    return services.get_stock_map()


def save_stock(levels: Dict[str, float]) -> int:
    if _server_up():
        try:
            return _http("PUT", "/stock", json={"levels": levels})["updated"]
        except Exception:
            pass
    from backend import services
    return services.set_stock(levels)


def clear_stock() -> None:
    if _server_up():
        try:
            _http("DELETE", "/stock")
            return
        except Exception:
            pass
    from backend import services
    services.clear_stock()


def log_event(kind: str, body_shape: Optional[str] = None, color_tone: Optional[str] = None,
              item: Optional[str] = None) -> None:
    """Never lets a logging problem break the page."""
    try:
        if _server_up():
            _http("POST", "/events", json={"kind": kind, "body_shape": body_shape, "color_tone": color_tone, "item": item})
        else:
            from backend import services
            services.log_event(kind, body_shape, color_tone, item)
    except Exception:
        pass


def engagement_summary() -> dict:
    empty = {"total_events": 0, "shape_reads": 0, "size_reads": 0, "top_sizes": [], "picks_viewed": 0, "tryons": 0, "top_shapes": [], "top_tryons": []}
    try:
        if _server_up():
            return _http("GET", "/events/summary")
        from backend import services
        return services.engagement_summary()
    except Exception:
        return empty


def styles_for(body_shape: str, color_tone: Optional[str] = None):
    if _server_up():
        try:
            return _http("GET", "/styles", params={"body_shape": body_shape, "color_tone": color_tone})["recommended_styles"]
        except Exception:
            pass
    from backend import services
    return services.styles_for(body_shape, color_tone)
