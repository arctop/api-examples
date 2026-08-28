# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31"]
# ///
"""List a session's score CSVs and download them.

Usage:
    uv run examples/download_outputs.py <session-id> [--dir outputs]
    uv run examples/download_outputs.py            # newest completed session with outputs

Raw EEG is not reachable through this API; outputs are the per-paradigm score
CSVs that apps wrote for the session.

Reference: https://docs.arctop.com/api/dev/v1/docs
(GET /api/dev/v1/sessions/{id}/outputs and .../outputs/{filename})
"""

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urljoin

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


def get(session: requests.Session, path: str, **kwargs) -> requests.Response:
    resp = session.get(urljoin(ORIGIN, path), timeout=60, **kwargs)
    if not resp.ok:
        fail(resp)
    return resp


def newest_session_with_outputs(session: requests.Session) -> str:
    resp = get(session, "/api/dev/v1/sessions",
               params={"status": "completed", "per_page": 25})
    for row in resp.json()["data"]:
        outputs = get(session,
                      f"/api/dev/v1/sessions/{row['id']}/outputs").json()["data"]
        if outputs:
            return row["id"]
    sys.exit("No completed session with outputs found on the first page.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("session_id", nargs="?",
                        help="session to download; omit for the newest "
                             "completed session that has outputs")
    parser.add_argument("--dir", default="outputs",
                        help="download directory (default: outputs/)")
    args = parser.parse_args()

    http = requests.Session()
    http.headers["Authorization"] = f"Bearer {api_key()}"

    session_id = args.session_id or newest_session_with_outputs(http)
    outputs = get(http, f"/api/dev/v1/sessions/{session_id}/outputs").json()["data"]
    if not outputs:
        sys.exit(f"Session {session_id} has no outputs.")

    target = Path(args.dir) / session_id
    target.mkdir(parents=True, exist_ok=True)
    print(f"session {session_id}: {len(outputs)} output file(s)")

    for output in outputs:
        print(f"  {output['filename']}  app={output['app_name']} "
              f"paradigm={output['paradigm']} {output['size_bytes']} bytes")
        resp = http.get(urljoin(ORIGIN, output["download_url"]),
                        timeout=300, stream=True)
        if not resp.ok:
            fail(resp)
        path = target / output["filename"]
        with open(path, "wb") as f:
            f.writelines(resp.iter_content(chunk_size=65536))

    print(f"downloaded to {target}/")


if __name__ == "__main__":
    main()
