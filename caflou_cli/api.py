import os
from typing import Any, Optional, Protocol

import httpx

from caflou_cli.config import load_config, resolve_account_id
from caflou_cli.output import error

BASE_URL = "https://app.caflou.com"


class ClientProtocol(Protocol):
    """Structural interface satisfied by CaflouClient and test fakes alike."""

    @property
    def account_id(self) -> str: ...
    def get(self, path: str, params: Optional[dict] = None) -> Any: ...
    def list(self, resource: str, page: int = 1, per: int = 20, filters: Optional[dict] = None) -> dict: ...
    def list_all(self, resource: str, filters: Optional[dict] = None) -> list: ...
    def post(self, path: str, data: dict) -> Any: ...
    def patch(self, path: str, data: dict) -> Any: ...
    def delete(self, path: str) -> None: ...


class CaflouClient:
    def __init__(self, token: str, account_id: str):
        self._account_id = account_id
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    @property
    def account_id(self) -> str:
        return self._account_id

    def _handle(self, response: httpx.Response) -> Any:
        if response.status_code == 401:
            error("Authentication failed. Run 'caflou auth login' to refresh your token.", 2)
        elif response.status_code == 403:
            error("Permission denied.", 4)
        elif response.status_code == 404:
            error("Resource not found.", 3)
        elif not response.is_success:
            error(f"API error {response.status_code}: {response.text[:300]}", 1)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def get(self, path: str, params: Optional[dict] = None) -> Any:
        url = f"/api/v1/{self._account_id}/{path}"
        return self._handle(self._http.get(url, params=params))

    def list(
        self,
        resource: str,
        page: int = 1,
        per: int = 20,
        filters: Optional[dict] = None,
    ) -> dict:
        params: dict = {"page": page, "per": per}
        if filters:
            for k, v in filters.items():
                params[f"filter[{k}]"] = v
        return self.get(resource, params)

    def post(self, path: str, data: dict) -> Any:
        url = f"/api/v1/{self._account_id}/{path}"
        return self._handle(self._http.post(url, json=data))

    def patch(self, path: str, data: dict) -> Any:
        url = f"/api/v1/{self._account_id}/{path}"
        return self._handle(self._http.patch(url, json=data))

    def delete(self, path: str) -> None:
        url = f"/api/v1/{self._account_id}/{path}"
        self._handle(self._http.delete(url))

    def list_all(self, resource: str, filters: Optional[dict] = None) -> list:
        import typer

        first = self.list(resource, page=1, per=100, filters=filters)
        total = first.get("total_results", 0)
        if total > 500:
            typer.echo(
                f"Warning: fetching all {total} results across multiple pages, this may be slow...",
                err=True,
            )

        results = list(first.get("results", []))
        total_pages = first.get("total_pages", 1)

        for page in range(2, total_pages + 1):
            data = self.list(resource, page=page, per=100, filters=filters)
            results.extend(data.get("results", []))

        return results


# ── module-level auth functions ───────────────────────────────────────────────

def login(email: str, password: str) -> dict:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        r = client.post(
            "/api/v1/login",
            auth=(email, password),
            headers={"Accept": "application/json"},
        )
        if r.status_code == 401:
            error("Invalid email or password.", 2)
        if not r.is_success:
            error(f"Login failed: {r.status_code}", 1)
        return r.json()


def get_accounts(token: str) -> list:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        r = client.get(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        if not r.is_success:
            error(f"Failed to fetch accounts: {r.status_code}", 1)
        return r.json()


def get_client(account_override: Optional[str] = None) -> CaflouClient:
    config = load_config()

    token = os.environ.get("CAFLOU_TOKEN") or config.get("token")
    if not token:
        error("Not authenticated. Run 'caflou auth login'.", 2)

    account_id = (
        account_override
        or os.environ.get("CAFLOU_ACCOUNT_ID")
        or config.get("default_account_id")
    )
    if not account_id:
        error("No account selected. Run 'caflou auth login'.", 2)

    account_id = resolve_account_id(account_id, config)

    return CaflouClient(token=token, account_id=account_id)
