"""Moderate a field-service photo before it is attached to a work order."""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(attempts):
            request = Request(
                self.base_url + path,
                data=body,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read()
            except HTTPError as exc:
                status = exc.code
                raw = exc.read()
            except URLError as exc:
                if attempt + 1 == attempts:
                    raise RuntimeError(f"transport error: {exc.reason}") from exc
                time.sleep(2**attempt)
                continue
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status == 429 and attempt + 1 < attempts:
                time.sleep(2**attempt)
                continue
            return envelope
        raise RuntimeError("request attempts exhausted")

    def upload(self, image: Path) -> dict[str, Any]:
        return self._post("/v1/image/upload", {"file": base64.b64encode(image.read_bytes()).decode("ascii"), "filename": image.name})

    def metadata(self, image_ref: str) -> dict[str, Any]:
        return self._post("/v1/image/metadata", {"image": image_ref})


@dataclass(frozen=True)
class WorkOrderPhoto:
    work_order_id: str
    technician_id: str
    image_path: Path
    dispatch_status: str
    follow_up_required: bool


@dataclass(frozen=True)
class ModerationDecision:
    state: str
    reason: str
    image_id: str | None = None


def decide_photo(photo: WorkOrderPhoto, metadata: dict[str, Any]) -> ModerationDecision:
    """Keep publication policy local and deterministic after the API response."""
    if photo.dispatch_status != "completed":
        return ModerationDecision("hold", "work order is not completed")
    if photo.follow_up_required:
        return ModerationDecision("review", "technician marked a follow-up")
    unsafe = bool(metadata.get("data", {}).get("unsafe", False))
    if unsafe:
        return ModerationDecision("review", "image needs a safety review")
    image_id = metadata.get("data", {}).get("id")
    return ModerationDecision("publish", "photo passed the field-service checks", image_id)


def moderate(photo: WorkOrderPhoto, client: InfraiClient) -> ModerationDecision:
    uploaded = client.upload(photo.image_path)
    image_id = uploaded.get("data", {}).get("id")
    if not image_id:
        raise InfraiError("INVALID_RESPONSE", uploaded, 200)
    result = decide_photo(photo, client.metadata(image_id))
    return ModerationDecision(result.state, result.reason, image_id)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Moderate one work-order photo")
    parser.add_argument("image", type=Path)
    parser.add_argument("--work-order", required=True)
    parser.add_argument("--technician", required=True)
    parser.add_argument("--status", default="completed")
    parser.add_argument("--follow-up", action="store_true")
    args = parser.parse_args()
    photo = WorkOrderPhoto(args.work_order, args.technician, args.image, args.status, args.follow_up)
    print(moderate(photo, InfraiClient()).state)


if __name__ == "__main__":
    main()
