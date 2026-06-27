"""In-memory test double satisfying ClientProtocol — no HTTP calls."""
from typing import Any, Optional


class FakeClient:
    """Drop-in replacement for CaflouClient in tests.

    Usage:
        fake = FakeClient()
        fake.seed("LIST", "tasks", {"results": [...], "total_results": 1, "total_pages": 1})
        fake.seed("GET", "tasks/42", {"id": 42, "name": "My Task"})
        fake.seed("POST", "tasks", {"id": 99, "name": "New Task"})

        with patch("caflou_cli.commands.task.get_client", return_value=fake):
            result = runner.invoke(app, ["task", "list"])

        assert fake.calls[0] == {"method": "LIST", "resource": "tasks", ...}
    """

    def __init__(self, account_id: str = "test-account"):
        self._account_id = account_id
        self.calls: list[dict] = []
        self._responses: dict[str, Any] = {}

    def seed(self, method: str, key: str, response: Any) -> "FakeClient":
        """Configure a canned response.

        method: GET | LIST | POST | PATCH | DELETE
        key: resource name for LIST, path for everything else
        Returns self so calls can be chained.
        """
        self._responses[f"{method.upper()}:{key}"] = response
        return self

    @property
    def account_id(self) -> str:
        return self._account_id

    def get(self, path: str, params: Optional[dict] = None) -> Any:
        self.calls.append({"method": "GET", "path": path, "params": params})
        return self._responses.get(f"GET:{path}", {})

    def list(self, resource: str, page: int = 1, per: int = 20, filters: Optional[dict] = None) -> dict:
        self.calls.append({"method": "LIST", "resource": resource, "page": page, "per": per, "filters": filters})
        default: dict = {"results": [], "total_results": 0, "total_pages": 1}
        return self._responses.get(f"LIST:{resource}", default)

    def list_all(self, resource: str, filters: Optional[dict] = None) -> list:
        self.calls.append({"method": "LIST_ALL", "resource": resource, "filters": filters})
        resp = self._responses.get(f"LIST:{resource}", {"results": []})
        if isinstance(resp, dict):
            return resp.get("results", [])
        return list(resp)

    def post(self, path: str, data: dict) -> Any:
        self.calls.append({"method": "POST", "path": path, "data": data})
        default: dict = {"id": 9999, **data}
        return self._responses.get(f"POST:{path}", default)

    def patch(self, path: str, data: dict) -> Any:
        self.calls.append({"method": "PATCH", "path": path, "data": data})
        return self._responses.get(f"PATCH:{path}", {**data})

    def delete(self, path: str) -> None:
        self.calls.append({"method": "DELETE", "path": path})
