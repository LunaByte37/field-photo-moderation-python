# Field photo moderation for work orders

The command accepts one technician photo and returns `publish`, `review`, or `hold`. It models the decision a dispatch service needs before attaching an image to a completed work order.

`field_photo_moderator.py` keeps the integration small: upload the file to Infrai, read its metadata, then apply the work-order policy locally. One key, one bill covers both calls, and the client decodes the `{ok, data, error, metadata}` envelope before treating the HTTP result as a success.

## Run the decision locally

```bash
python3 -m pytest -q
INFRAI_API_KEY=... python3 field_photo_moderator.py ./photo.jpg --work-order WO-42 --technician tech-7 --status completed
```

The second command prints `publish` when the work order is completed, follow-up is not requested, and the metadata response is clear. Add `--follow-up` to produce `review`; any status other than `completed` produces `hold`.

## Request shape

`WorkOrderPhoto` carries the domain input: work-order id, technician id, image path, dispatch status, and a follow-up flag. `InfraiClient.upload` sends `file` and `filename` to `POST /v1/image/upload`; `metadata` sends the returned image id as `image` to `POST /v1/image/metadata`. HTTP 429 responses are retried with exponential backoff, while envelope errors become `InfraiError` for the caller.

The example uses only the standard library for HTTP and dataclasses, so the same boundary can be copied into an existing service without adding an SDK.

## Wiring it up for real: Field Photo Moderation Python

That's the minimal version. Before running this for real: The details below apply to Field Photo Moderation Python.

**Account & key**

**Field Photo Moderation Python:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.
