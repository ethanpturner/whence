"""The registry seam.

`RecordedRegistry` replays captured interactions offline and is what the default test run uses; no
credential is required and no network call is made (DEC-009).

Response classification is DEC-014 and is decided by **status code alone**. Registry error strings
describe the most common cause rather than the actual one -- `withdrawn-base` captures a 401 whose
body reads "Invalid username or password" for a request that carried no credentials -- so reading
the prose would import the registry's guess about the caller into our model of the world.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

from whence.domain import ResolutionClass


def classify(status: int) -> ResolutionClass:
    if status in (429,) or status >= 500 or status == 0:
        return ResolutionClass.TRANSIENT
    if status in (401, 403):
        return ResolutionClass.INCONCLUSIVE
    return ResolutionClass.CONCLUSIVE


@dataclass(frozen=True)
class Response:
    status: int
    body: dict[str, Any] | list[Any] | None
    location: str | None = None

    @property
    def resolution(self) -> ResolutionClass:
        return classify(self.status)

    @property
    def redirected(self) -> bool:
        return self.status in (301, 302, 307, 308) and self.location is not None


class Registry(Protocol):
    def get(self, path: str) -> Response: ...


class RecordedRegistry:
    """Replays a scenario's `recorded/` directory. Unknown paths are a fixture defect, not a 404."""

    def __init__(self, recorded_dir: Path) -> None:
        self._dir = recorded_dir
        manifest = yaml.safe_load((recorded_dir / "manifest.yaml").read_text())
        self._by_path: dict[str, Response] = {}
        for entry in manifest.get("interactions") or []:
            request = str(entry["request"])
            path = request.split(" ", 1)[1] if " " in request else request
            body: dict[str, Any] | list[Any] | None = None
            if entry.get("body"):
                raw = (recorded_dir / str(entry["body"])).read_text()
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError:
                    body = {"_raw": raw}
            self._by_path[path] = Response(
                status=int(entry["status"]), body=body, location=entry.get("location")
            )

    def get(self, path: str) -> Response:
        try:
            return self._by_path[path]
        except KeyError:
            raise LookupError(
                f"{path} is not in the recording. A missing interaction is a fixture defect; it is "
                f"not a 404, and inventing one would put a fabricated response shape into the "
                f"benchmark."
            ) from None


class LiveRegistry:
    """Real HTTP. Never used by the default test run; a connection failure is transient."""

    def __init__(self, base: str = "https://huggingface.co", timeout: float = 20.0) -> None:
        self._base, self._timeout = base.rstrip("/"), timeout

    def get(self, path: str) -> Response:
        import httpx

        try:
            r = httpx.get(f"{self._base}{path}", timeout=self._timeout, follow_redirects=False)
        except httpx.HTTPError:
            return Response(status=0, body=None)  # transient; produces no verdict
        location = r.headers.get("location")
        body: dict[str, Any] | list[Any] | None
        try:
            body = r.json()
        except ValueError:
            body = None
        return Response(status=r.status_code, body=body, location=location)
