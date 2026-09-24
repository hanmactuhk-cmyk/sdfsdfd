import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class WebhookError(RuntimeError):
    pass


class WebhookClient:
    def __init__(self, base_url="http://127.0.0.1:8765", api_key=""):
        self.base_url = base_url.strip().rstrip("/")
        self.api_key = api_key.strip()

    def _request(self, method, path, body=None, timeout=60):
        data = None
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                content_type = response.headers.get("Content-Type", "")
                if "json" in content_type or raw[:1] in (b"{", b"["):
                    return json.loads(raw.decode("utf-8"))
                return raw
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            raise WebhookError(f"HTTP {exc.code}: {raw[:1200]}") from exc
        except urllib.error.URLError as exc:
            raise WebhookError(f"Connection failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise WebhookError("Request timed out") from exc

    def health(self):
        return self._request("GET", "/api/health")

    def generate(self, kind, payload):
        allowed = {"image", "video", "grok", "meta", "openai", "upscale"}
        if kind not in allowed:
            raise WebhookError(f"Unsupported endpoint: {kind}")
        return self._request("POST", f"/api/{kind}/generate", payload)

    def status(self, task_id):
        return self._request("GET", f"/api/status/{urllib.parse.quote(str(task_id), safe='')}")

    def result(self, task_id):
        return self._request("GET", f"/api/result/{urllib.parse.quote(str(task_id), safe='')}")

    def tasks(self):
        return self._request("GET", "/api/tasks")

    def wait(self, task_id, interval=3, timeout=3600, on_update=None):
        started = time.time()
        while time.time() - started < timeout:
            status = self.status(task_id)
            if on_update:
                on_update(status)
            state = str(status.get("status", status.get("state", ""))).lower()
            if state in {"completed", "complete", "success", "succeeded"}:
                return self.result(task_id)
            if state in {"failed", "error", "cancelled"}:
                raise WebhookError(str(status))
            time.sleep(interval)
        raise WebhookError("Task polling timed out")

    def download(self, filename, destination):
        encoded = urllib.parse.quote(str(filename), safe="")
        data = self._request("GET", f"/api/files/{encoded}")
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode("utf-8")
        Path(destination).write_bytes(data)
        return destination
