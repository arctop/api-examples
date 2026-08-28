# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31"]
# ///
"""List recording sessions in the key's scope.

Usage:
    uv run examples/list_sessions.py [--status completed] [--device MW75]
        [--user <uuid>] [--from 2026-08-01] [--to 2026-08-28]
        [--sort started_at] [--order desc] [--page 1] [--per-page 25]

Reference: https://docs.arctop.com/api/dev/v1/docs (GET /api/dev/v1/sessions)
"""

import argparse
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


def fail(resp: requests.Response) -> None:
    try:
        body = resp.json()
        detail = f"{body.get('error', '')}: {body.get('message', '')}"
    except ValueError:
        detail = resp.text.strip()
    sys.exit(f"HTTP {resp.status_code} {detail}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", choices=["active", "completed", "error"])
    parser.add_argument("--device", help="filter by EEG device type")
    parser.add_argument("--user", help="filter to one user id")
    parser.add_argument("--from", dest="from_", metavar="FROM",
                        help="RFC 3339 instant or YYYY-MM-DD")
    parser.add_argument("--to", help="RFC 3339 instant or YYYY-MM-DD")
    parser.add_argument("--sort", choices=["started_at", "duration_seconds",
                                           "packet_count", "eeg_device_type"])
    parser.add_argument("--order", choices=["asc", "desc"])
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--per-page", type=int, default=25)
    args = parser.parse_args()

    params = {
        "status": args.status,
        "eeg_device_type": args.device,
        "user_id": args.user,
        "from": args.from_,
        "to": args.to,
        "sort": args.sort,
        "order": args.order,
        "page": args.page,
        "per_page": args.per_page,
    }
    params = {k: v for k, v in params.items() if v is not None}

    resp = requests.get(
        f"{ORIGIN}/api/dev/v1/sessions",
        params=params,
        headers={"Authorization": f"Bearer {api_key()}"},
        timeout=30,
    )
    if not resp.ok:
        fail(resp)

    body = resp.json()
    sessions = body["data"]
    pagination = body["pagination"]

    print(f"page {pagination['page']}/{pagination['total_pages']}, "
          f"{pagination['total']} session(s) total\n")
    if not sessions:
        return

    header = f"{'id':36}  {'started_at':25}  {'status':9}  {'device':8}  " \
             f"{'seconds':>7}  {'packets':>9}  user_id"
    print(header)
    print("-" * len(header))
    for s in sessions:
        duration = s["duration_seconds"]
        print(f"{s['id']:36}  {s['started_at']:25}  {s['status']:9}  "
              f"{s['eeg_device_type']:8}  "
              f"{duration if duration is not None else '-':>7}  "
              f"{s['packet_count']:>9}  {s['user_id']}")


if __name__ == "__main__":
    main()
