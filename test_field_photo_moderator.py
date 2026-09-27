import base64
from pathlib import Path
from unittest.mock import patch

from field_photo_moderator import InfraiClient, WorkOrderPhoto, decide_photo


def test_upload_encodes_file_as_base64(tmp_path):
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"\xff\xd8\x00\xfe")
    client = InfraiClient(api_key="test-key")
    with patch.object(client, "_post", return_value={}) as post:
        client.upload(image)
    post.assert_called_once_with(
        "/v1/image/upload",
        {"file": base64.b64encode(image.read_bytes()).decode("ascii"), "filename": "photo.jpg"},
    )


def test_follow_up_routes_completed_photo_to_review():
    photo = WorkOrderPhoto("WO-42", "tech-7", Path("photo.jpg"), "completed", True)
    decision = decide_photo(photo, {"data": {"unsafe": False}})
    assert decision.state == "review"
    assert decision.reason == "technician marked a follow-up"


def test_completed_photo_is_published_when_metadata_is_clear():
    photo = WorkOrderPhoto("WO-42", "tech-7", Path("photo.jpg"), "completed", False)
    assert decide_photo(photo, {"data": {"unsafe": False}}).state == "publish"
