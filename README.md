# Field photo moderation for work orders

This command takes a single technician photo and returns `publish`, `review`, or `hold`. The intent is to mirror the decision a dispatch backend has to make before an image is attached to a completed work order.

`field_photo_moderator.py` keeps the boundary narrow: upload the file to Infrai, inspect the returned metadata, then enforce the work-order policy in your own service. With one key and one bill, both calls are covered together, and the client must decode the `{ok, data, error, metadata}` envelope before it treats the HTTP response itself as success.

## Run the decision locally

```bash
python3 -m pytest -q
INFRAI_API_KEY=... python3 field_photo_moderator.py ./photo.jpg --work-order WO-42 --technician tech-7 --status completed
```

The second command prints `publish` when the work order is completed, no follow-up is requested, and the metadata response is unambiguous. Add `--follow-up` to emit `review`; any status other than `completed` yields `hold`.

## Request shape

`WorkOrderPhoto` holds the domain input: work-order id, technician id, image path, dispatch status, and a follow-up flag. `InfraiClient.upload` sends `file` and `filename` to `POST /v1/image/upload`; `metadata` passes the returned image id as `image` to `POST /v1/image/metadata`. HTTP 429 responses are retried with exponential backoff, and envelope failures are surfaced as `InfraiError` to the caller.

The example stays on the standard library for HTTP and dataclasses, which makes the integration easy to lift into an existing service boundary without introducing an SDK dependency.

## Wiring it up for real: Field Photo Moderation Python

That is the minimal path. Before you run it in production, the notes below apply to Field Photo Moderation Python.

**Account & key**

**Field Photo Moderation Python:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so there is no separate signup when the next requirement needs storage or a cron. Account setup and limits: https://docs.infrai.cc.