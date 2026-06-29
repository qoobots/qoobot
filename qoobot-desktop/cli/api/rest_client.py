"""
qoodev REST API client — HTTP-based remote integration.

对标：OpenAPI / Swagger
提供技能管理、仿真控制、数据查询等 REST 端点。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, urljoin


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class APIResponse:
    status_code: int
    headers: Dict[str, str]
    data: Any
    elapsed_ms: float = 0.0


class QooDevRESTClient:
    """REST API client for qoodev remote services.

    Usage::

        client = QooDevRESTClient(base_url="http://robot.local:8080")
        skills = client.list_skills()
        client.start_simulation("warehouse_navigation")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        timeout_s: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = timeout_s
        self._session_headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "qoodev-rest/1.0",
        }
        if api_key:
            self._session_headers["Authorization"] = f"Bearer {api_key}"

    # -- low-level HTTP ------------------------------------------------------

    def request(
        self,
        method: HTTPMethod,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        if params:
            url += "?" + urlencode(params)

        req_headers = dict(self._session_headers)
        if headers:
            req_headers.update(headers)

        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = Request(url, data=data, headers=req_headers, method=method.value)

        t0 = time.perf_counter()
        try:
            with urlopen(req, timeout=self.timeout_s) as resp:
                elapsed = (time.perf_counter() - t0) * 1000
                resp_data = resp.read()
                try:
                    parsed = json.loads(resp_data)
                except json.JSONDecodeError:
                    parsed = resp_data.decode("utf-8", errors="replace")

                return APIResponse(
                    status_code=resp.status,
                    headers=dict(resp.headers),
                    data=parsed,
                    elapsed_ms=elapsed,
                )
        except HTTPError as e:
            elapsed = (time.perf_counter() - t0) * 1000
            return APIResponse(status_code=e.code, headers=dict(e.headers), data={"error": str(e)}, elapsed_ms=elapsed)
        except URLError as e:
            elapsed = (time.perf_counter() - t0) * 1000
            return APIResponse(status_code=0, headers={}, data={"error": str(e.reason)}, elapsed_ms=elapsed)

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> APIResponse:
        return self.request(HTTPMethod.GET, path, params=params)

    def post(self, path: str, body: Any = None, params: Optional[Dict[str, Any]] = None) -> APIResponse:
        return self.request(HTTPMethod.POST, path, params=params, body=body)

    def put(self, path: str, body: Any = None, params: Optional[Dict[str, Any]] = None) -> APIResponse:
        return self.request(HTTPMethod.PUT, path, params=params, body=body)

    def delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> APIResponse:
        return self.request(HTTPMethod.DELETE, path, params=params)

    # -- skill management ----------------------------------------------------

    def list_skills(self, robot_id: Optional[str] = None) -> APIResponse:
        params = {"robot_id": robot_id} if robot_id else None
        return self.get("/api/v1/skills", params=params)

    def get_skill(self, skill_id: str) -> APIResponse:
        return self.get(f"/api/v1/skills/{skill_id}")

    def install_skill(self, skill_id: str, robot_id: str) -> APIResponse:
        return self.post(f"/api/v1/skills/{skill_id}/install", body={"robot_id": robot_id})

    def uninstall_skill(self, skill_id: str, robot_id: str) -> APIResponse:
        return self.delete(f"/api/v1/skills/{skill_id}/install", params={"robot_id": robot_id})

    def upload_skill(self, package_path: str, metadata: Dict[str, Any]) -> APIResponse:
        # multipart would be used in production; simplified here
        return self.post("/api/v1/skills", body={"package_path": package_path, "metadata": metadata})

    # -- simulation control --------------------------------------------------

    def list_simulations(self) -> APIResponse:
        return self.get("/api/v1/simulations")

    def start_simulation(self, scene_name: str, config: Optional[Dict[str, Any]] = None) -> APIResponse:
        return self.post("/api/v1/simulations", body={"scene": scene_name, "config": config or {}})

    def stop_simulation(self, simulation_id: str) -> APIResponse:
        return self.delete(f"/api/v1/simulations/{simulation_id}")

    def get_simulation_state(self, simulation_id: str) -> APIResponse:
        return self.get(f"/api/v1/simulations/{simulation_id}/state")

    def step_simulation(self, simulation_id: str, steps: int = 1) -> APIResponse:
        return self.post(f"/api/v1/simulations/{simulation_id}/step", body={"steps": steps})

    # -- data access ---------------------------------------------------------

    def list_datasets(self) -> APIResponse:
        return self.get("/api/v1/datasets")

    def get_dataset(self, dataset_id: str) -> APIResponse:
        return self.get(f"/api/v1/datasets/{dataset_id}")

    def query_dataset(
        self,
        dataset_id: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> APIResponse:
        params = {"limit": limit, "offset": offset}
        return self.post(f"/api/v1/datasets/{dataset_id}/query", body=filters or {}, params=params)

    # -- model inference -----------------------------------------------------

    def list_models(self) -> APIResponse:
        return self.get("/api/v1/models")

    def run_inference(
        self,
        model_id: str,
        inputs: Dict[str, Any],
        device: str = "auto",
    ) -> APIResponse:
        return self.post(f"/api/v1/models/{model_id}/infer", body={"inputs": inputs, "device": device})

    def get_model_metrics(self, model_id: str) -> APIResponse:
        return self.get(f"/api/v1/models/{model_id}/metrics")

    # -- robot telemetry -----------------------------------------------------

    def get_robot_status(self, robot_id: str) -> APIResponse:
        return self.get(f"/api/v1/robots/{robot_id}/status")

    def list_robots(self) -> APIResponse:
        return self.get("/api/v1/robots")

    def send_command(self, robot_id: str, command: str, params: Optional[Dict[str, Any]] = None) -> APIResponse:
        return self.post(f"/api/v1/robots/{robot_id}/command", body={"command": command, "params": params or {}})

    def subscribe_telemetry(
        self,
        robot_id: str,
        topics: List[str],
        callback_url: str,
    ) -> APIResponse:
        return self.post(f"/api/v1/robots/{robot_id}/telemetry/subscribe", body={
            "topics": topics, "callback_url": callback_url,
        })

    # -- profiling -----------------------------------------------------------

    def start_profiling(self, robot_id: str, duration_s: float = 30.0) -> APIResponse:
        return self.post(f"/api/v1/robots/{robot_id}/profile/start", body={"duration_s": duration_s})

    def stop_profiling(self, robot_id: str) -> APIResponse:
        return self.post(f"/api/v1/robots/{robot_id}/profile/stop")

    def get_profile_report(self, robot_id: str) -> APIResponse:
        return self.get(f"/api/v1/robots/{robot_id}/profile/report")

    # -- health & system -----------------------------------------------------

    def health_check(self) -> APIResponse:
        return self.get("/api/v1/health")

    def get_version(self) -> APIResponse:
        return self.get("/api/v1/version")


# ---------------------------------------------------------------------------
# API Server stub (FastAPI-based)
# ---------------------------------------------------------------------------

def create_rest_server(host: str = "0.0.0.0", port: int = 8080) -> Any:
    """Create a minimal REST API server for local development."""
    try:
        from fastapi import FastAPI  # type: ignore
        import uvicorn  # type: ignore
    except ImportError:
        raise ImportError("fastapi + uvicorn required for REST server")

    app = FastAPI(title="qoodev API", version="1.0.0")

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "timestamp": time.time()}

    @app.get("/api/v1/version")
    async def version():
        return {"version": "1.0.0", "build": "dev"}

    @app.get("/api/v1/skills")
    async def list_skills():
        return {"skills": []}

    @app.post("/api/v1/simulations")
    async def start_simulation(body: Dict[str, Any]):
        return {"simulation_id": "sim_001", "status": "starting", "scene": body.get("scene")}

    return app, uvicorn
