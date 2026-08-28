# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31"]
# ///
"""Stamp a marker into one or more currently live recordings.

Usage:
    uv run examples/inject_marker.py stimulus --label face-07
    uv run examples/inject_marker.py stimulus --label face-07 --user <uuid> --user <uuid>

Untargeted (no --user): the marker lands in the key owner's own live
recording; injecting while the owner is not streaming is a 404
no_active_session. Targeted (--user, repeatable): the marker is stamped into
each named user's live recording; a user with no live recording in the key's
scope is reported as skipped, and every-target-skipped is still a 200.

The stored row reads back through GET .../markers with app_id "dev_api",
event_type "dev_marker", and label "<event_type>:<label>".

Reference: https://docs.arctop.com/api/dev/v1/docs
(POST /api/dev/v1/sessions/current/markers)
"""

import argparse
import json
import os
import sys

import requests

ORIGIN = os.environ.get("ARCTOP_ORIGIN", "https://hegemon42.arctop.com")


def api_key() -> str:
    key = os.environ.get("ARCTOP_API_KEY")
    if not key:
        sys.exit(
            "ARCTOP_API_KEY is not set. Create a key on the dashboard "
            "(Developers page) and export it first."
        )
    return key


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event_type", help="required marker event type")
    parser.add_argument("--label", help="optional marker label")
    parser.add_argument("--timestamp", type=int,
                        help="epoch milliseconds; defaults to arrival time")
    parser.add_argument("--user", action="append", default=[],
                        help="target user id; repeat for several users")
    args = parser.parse_args()

    body = {"event_type": args.event_type}
    if args.label is not None:
        body["label"] = args.label
    if args.timestamp is not None:
        body["timestamp"] = args.timestamp

    resp = requests.post(
        f"{ORIGIN}/api/dev/v1/sessions/current/markers",
        params=[("user_id", u) for u in args.user],
        json=body,
        headers={"Authorization": f"Bearer {api_key()}"},
        timeout=30,
    )

    try:
        payload = resp.json()
    except ValueError:
        sys.exit(f"HTTP {resp.status_code} {resp.text.strip()}")

    if resp.status_code == 404 and payload.get("error") == "no_active_session":
        sys.exit("Nothing is recording for the key owner right now "
                 "(untargeted injection needs a live session).")
    if not resp.ok:
        sys.exit(f"HTTP {resp.status_code} "
                 f"{payload.get('error', '')}: {payload.get('message', '')}")

    if "results" in payload:
        # Targeted form: per-user outcomes, in request order.
        print(f"marker: {json.dumps(payload['marker'])}")
        for result in payload["results"]:
            line = f"  {result['user_id']}: {result['status']}"
            if result["status"] == "written":
                line += f" (session {result['session_id']})"
            print(line)
    else:
        # Untargeted form: the 201 echoes the stored row byte for byte.
        print(f"written to session {payload['session_id']}")
        print(f"marker: {json.dumps(payload['marker'])}")


if __name__ == "__main__":
    main()
