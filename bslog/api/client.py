"""HTTP client for Better Stack APIs."""

import json
import os
import sys
from base64 import b64encode
from typing import Any

import httpx

from bslog.utils.config import DEFAULT_QUERY_BASE_URL, get_api_token, load_config

TELEMETRY_BASE_URL = "https://telemetry.betterstack.com/api/v1"
DEFAULT_TIMEOUT_S = 30


class BetterStackClient:
    def __init__(self) -> None:
        self.token = get_api_token()
        self._client = httpx.Client(timeout=DEFAULT_TIMEOUT_S)

    def request(
        self, url: str, method: str = "GET", headers: dict[str, str] | None = None, body: str | None = None,
    ) -> Any:
        req_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        if headers:
            req_headers.update(headers)

        response = self._client.request(method, url, headers=req_headers, content=body)

        if not response.is_success:
            error = response.text
            raise RuntimeError(f"API request failed: {response.status_code} - {error}")

        return response.json()

    def telemetry(self, path: str) -> Any:
        url = f"{TELEMETRY_BASE_URL}{path}"
        return self.request(url)

    def query(self, sql: str, username: str | None = None, password: str | None = None) -> list[dict[str, Any]]:
        headers: dict[str, str] = {
            "Content-Type": "text/plain",
        }

        if username and password:
            auth = b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {auth}"
        else:
            headers["Authorization"] = f"Bearer {self.token}"

        config = load_config()
        query_base_url = config.queryBaseUrl or DEFAULT_QUERY_BASE_URL

        try:
            response = self._client.post(query_base_url, headers=headers, content=sql)
        except httpx.TimeoutException:
            raise RuntimeError("Query timed out after 30 seconds")

        if not response.is_success:
            error = response.text

            if response.status_code == 400 and "Malformed token" in error:
                api_token_status = "Set" if os.environ.get("BETTERSTACK_API_TOKEN") else "Not set"
                username_status = "Set" if os.environ.get("BETTERSTACK_QUERY_USERNAME") else "Not set"
                password_status = "Set" if os.environ.get("BETTERSTACK_QUERY_PASSWORD") else "Not set"
                raise RuntimeError(
                    f"Query API authentication failed: Malformed token\n\n"
                    f"This usually means your Query API credentials are not set.\n\n"
                    f"Current environment:\n"
                    f"  BETTERSTACK_API_TOKEN: {'✓' if api_token_status == 'Set' else '✗'} {api_token_status}\n"
                    f"  BETTERSTACK_QUERY_USERNAME: {'✓' if username_status == 'Set' else '✗'} {username_status}\n"
                    f"  BETTERSTACK_QUERY_PASSWORD: {'✓' if password_status == 'Set' else '✗'} {password_status}\n\n"
                    f"To fix this:\n"
                    f'1. Add these to your ~/.zshrc or ~/.bashrc:\n'
                    f'   export BETTERSTACK_QUERY_USERNAME="your_username"\n'
                    f'   export BETTERSTACK_QUERY_PASSWORD="your_password"\n\n'
                    f"2. Reload your shell:\n"
                    f"   source ~/.zshrc\n\n"
                    f"3. Or set them for this session:\n"
                    f'   export BETTERSTACK_QUERY_USERNAME="your_username"\n'
                    f'   export BETTERSTACK_QUERY_PASSWORD="your_password"\n\n'
                    f"To get Query API credentials:\n"
                    f"1. Go to Better Stack > Logs > Dashboards\n"
                    f'2. Click "Connect remotely"\n'
                    f"3. Create credentials and save them"
                )

            if response.status_code in (401, 403) or "Authentication failed" in error:
                if not username or not password:
                    raise RuntimeError(
                        "Query API authentication failed.\n\n"
                        "The Query API requires separate credentials from your API token.\n"
                        "To create credentials:\n"
                        "1. Go to Better Stack > Logs > Dashboards\n"
                        '2. Click "Connect remotely"\n'
                        "3. Create credentials and save them\n\n"
                        "Then set them as environment variables:\n"
                        'export BETTERSTACK_QUERY_USERNAME="your_username"\n'
                        'export BETTERSTACK_QUERY_PASSWORD="your_password"\n\n'
                        "Or pass them directly:\n"
                        'bslog tail --username "user" --password "pass"'
                    )
                raise RuntimeError("Authentication failed. Please check your Query API credentials.")

            raise RuntimeError(f"Query failed: {response.status_code} - {error}")

        text = response.text
        lines = [line for line in text.strip().split("\n") if line.strip()]
        rows: list[dict[str, Any]] = []

        for line in lines:
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    rows.append(parsed)
                else:
                    print(f"Unexpected row payload: {line}", file=sys.stderr)
            except json.JSONDecodeError:
                print(f"Failed to parse line: {line}", file=sys.stderr)

        return rows
