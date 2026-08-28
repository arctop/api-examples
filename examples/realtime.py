# /// script
# requires-python = ">=3.10"
# dependencies = ["websockets>=12.0"]
# ///
"""Listen on the realtime WebSocket and print what arrives.

Usage:
    uv run examples/realtime.py [--user <uuid> ...]

Connect once, at the start of the experiment, and wait: a valid key always
gets a socket. It reports stream_state for every user in scope immediately
and again on every change, then delivers live events as they arrive.
Connecting while nothing is streaming is normal and supported.

Every frame is a JSON object with a "type"; switch on type and nothing else.
The socket closes with a private-range code that echoes the corresponding
HTTP status; key off the numeric code, never the reason text:

    4401  key stopped authenticating (terminal, do not retry)
    4403  the key's developer group stopped authorizing (terminal here)
    4408  keepalive timeout            (reconnect with backoff)
    4429  slow consumer                (reconnecting immediately is legal)
    4500  internal error               (retryable)
    4503  server shutting realtime down (reconnect with backoff)

Reference: https://docs.arctop.com/api/dev/v1/docs (GET /api/dev/v1/realtime)
"""

import argparse
import json
import os
import sys
import time
from urllib.parse import urlencode

from websockets.exceptions import ConnectionClosed, InvalidStatus
from websockets.sync.client import connect

ORIGIN = os.environ.get("ARCTOP_ORIGIN", "https://hegemon42.arctop.com")
TERMINAL_CODES = {4401, 4403}
HEALTHY_SECONDS = 60


def api_key() -> str:
    key = os.environ.get("ARCTOP_API_KEY")
    if not key:
        sys.exit(
            "ARCTOP_API_KEY is not set. Create a key on the dashboard "
            "(Developers page) and export it first."
        )
    return key


def ws_url(users: list[str]) -> str:
    scheme = "wss" if ORIGIN.startswith("https") else "ws"
    url = f"{scheme}://{ORIGIN.split('://', 1)[1]}/api/dev/v1/realtime"
    if users:
        url += "?" + urlencode([("user_id", u) for u in users])
    return url


def print_frame(frame: dict) -> None:
    kind = frame.get("type")
    if kind == "stream_state":
        print(f"stream_state  user={frame['user_id']} state={frame['state']} "
              f"streamer_running={frame['streamer_running']} "
              f"attached={frame['attached']} session={frame['session_id'] or '-'}")
    elif kind == "event":
        event = frame.get("event", {})
        if event.get("type") == "devstream_gap":
            # The socket fell behind; the loss is reported in-band, never silent.
            print(f"GAP           user={frame['user_id']} {json.dumps(event)}")
        else:
            print(f"event         user={frame['user_id']} "
                  f"session={frame['session_id']} {json.dumps(event)}")
    elif kind == "closing":
        print(f"closing       code={frame['code']} reason={frame['reason']}")
    elif kind == "error":
        # Non-fatal; the connection stays up.
        print(f"error         {frame.get('error')}: {frame.get('message', '')}")
    else:
        # The type set may grow; existing types never change meaning.
        print(f"{kind or '?'}  {json.dumps(frame)}")


def listen_once(url: str, key: str) -> tuple[int | None, float]:
    """Read frames until the socket closes; return its code and uptime."""
    with connect(url, additional_headers={"Authorization": f"Bearer {key}"}) as ws:
        print(f"connected to {url}")
        opened = time.monotonic()
        while True:
            try:
                message = ws.recv()
            except ConnectionClosed as closed:
                code = closed.rcvd.code if closed.rcvd else None
                return code, time.monotonic() - opened
            print_frame(json.loads(message))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--user", action="append", default=[],
                        help="narrow the scope to this user id; repeatable")
    args = parser.parse_args()

    url = ws_url(args.user)
    key = api_key()
    backoff = 1
    while True:
        try:
            code, uptime = listen_once(url, key)
        except KeyboardInterrupt:
            return
        except InvalidStatus as err:
            # The handshake itself was refused, before any upgrade.
            status = err.response.status_code
            if status in (401, 403):
                sys.exit(f"handshake refused with HTTP {status}; check the "
                         "key. Not retrying.")
            print(f"handshake refused with HTTP {status}", file=sys.stderr)
            code, uptime = None, 0.0
        except OSError as err:
            print(f"connect failed: {err}", file=sys.stderr)
            code, uptime = None, 0.0

        if code in TERMINAL_CODES:
            sys.exit(f"socket closed {code}; the key or its group no longer "
                     "authorizes this stream. Not retrying.")
        if code == 1000:
            print("closed normally")
            return
        if uptime >= HEALTHY_SECONDS:
            # The socket was healthy; treat this as a fresh failure
            # rather than the next step of an escalating retry.
            backoff = 1
        delay = 1 if code == 4429 else backoff
        print(f"closed (code={code}); reconnecting in {delay}s", file=sys.stderr)
        time.sleep(delay)
        backoff = min(backoff * 2, 30)


if __name__ == "__main__":
    main()
