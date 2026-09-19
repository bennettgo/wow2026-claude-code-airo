"""Shared Workato Dev API HTTP client — DC resolution, retry/backoff, auth."""
import json
import os
import time
import requests

_DC_CHOICES = {"us", "eu", "jp", "sg", "au", "in", "il", "preview"}


def resolve_dc(dc: str) -> tuple[str, str]:
    dc = (dc or "us").lower()
    if dc not in _DC_CHOICES:
        raise ValueError(f"unknown WORKATO_DC {dc!r}; must be one of {sorted(_DC_CHOICES)}")
    if dc == "us":
        return "https://app.workato.com", "https://genie-api.workato.com"
    if dc == "preview":
        # Workato's internal pre-release stack, not a customer-facing DC —
        # confirmed live against /api/users/me for PSM-22639's repro setup.
        return "https://app.preview.workato.com", "https://genie-api.preview.workato.com"
    return f"https://app.{dc}.workato.com", f"https://genie-api.{dc}.workato.com"


def resolve_effective_dc(manifest: dict) -> str:
    """Pick the DC for a follow-on script: WORKATO_DC wins, manifest["dc"] is the fallback.

    init_suite.py records the DC it provisioned against in the manifest, so a user
    who provisioned on `eu` but forgot to export WORKATO_DC still targets `eu`
    instead of silently hitting `us` and getting confusing 401s.
    """
    env_dc = os.environ.get("WORKATO_DC")
    manifest_dc = manifest.get("dc")
    if env_dc and manifest_dc and env_dc.lower() != str(manifest_dc).lower():
        print(f"WARNING: WORKATO_DC={env_dc} overrides manifest's recorded dc={manifest_dc}")
    return env_dc or manifest_dc or "us"


DEFAULT_TIMEOUT_SECONDS = 120
# Raised from the original 30s: the Judge scoring recipe makes two sequential
# assign_task_to_genie calls internally (correctness, then completeness), and
# a real run observed a question that consistently timed out at 30s on both
# attempts (same question, both times — not random flakiness).


class WorkatoClient:
    def __init__(self, token: str, dc: str = "us", timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self.token = token
        self.dev_base, self.headless_base = resolve_dc(dc)
        self.timeout = timeout

    def call(self, method: str, path: str, body: dict | None = None,
              base: str | None = None, extra_headers: dict | None = None,
              max_retries: int = 5, timeout: int | None = None) -> tuple[int, dict]:
        url = f"{base or self.dev_base}{path}"
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)

        attempt = 0
        while True:
            try:
                resp = requests.request(method, url, json=body, headers=headers,
                                          timeout=timeout or self.timeout)
            except requests.exceptions.RequestException as e:
                # Transport-layer failure (connection reset, DNS, timeout). Treat it
                # exactly like a retryable 5xx so a single network blip cannot abort a
                # multi-hour ingestion/benchmark run. On exhaustion return a synthetic
                # terminal result instead of raising — call() never raises, by contract.
                attempt += 1
                if attempt >= max_retries:
                    return 599, {"error": str(e)}
                time.sleep(0.5 * (2 ** attempt))
                continue
            if resp.status_code == 429 or resp.status_code >= 500:
                attempt += 1
                if attempt >= max_retries:
                    return resp.status_code, self._parse(resp.text)
                time.sleep(0.5 * (2 ** attempt))
                continue
            return resp.status_code, self._parse(resp.text)

    @staticmethod
    def _parse(text: str) -> dict:
        try:
            return json.loads(text) if text else {}
        except json.JSONDecodeError:
            return {"raw": text}

    def must(self, status: int, body: dict, what: str) -> dict:
        if status >= 400:
            raise RuntimeError(f"{what} failed [{status}]: {body}")
        return body
