# Arctop Developer API examples

Runnable examples for the [Arctop developer API](https://docs.arctop.com): read access
to recording sessions, their score outputs and marker events, a live event stream, and
marker injection into running sessions.

- Rendered reference: https://docs.arctop.com
- Raw markdown (agent-friendly): https://docs.arctop.com/api/dev/v1/docs

The reference is complete and contract-stable: a path not listed there does not exist,
fields are added but never renamed or removed, and breaking changes ship under a new
version prefix.

## Get an API key

Keys are self-serve. Sign in to the dashboard and create one on the Developers page:

https://hegemon42.arctop.com/dashboard/developers/keys

A key begins with `ak_` and is shown once, at creation. It travels in an
`Authorization: Bearer <key>` header on every request, including the WebSocket
handshake. A personal key reads your own data; a group key reads your developer
group's members per the scope rules in the reference.

## Setup

```bash
export ARCTOP_API_KEY=ak_...
# Optional; this is the default:
export ARCTOP_ORIGIN=https://hegemon42.arctop.com
```

Each example is a single self-contained file with inline dependency metadata
(PEP 723), so with [uv](https://docs.astral.sh/uv/) there is nothing to install:

```bash
uv run examples/list_sessions.py
```

Or with plain pip, on Python 3.10 or newer:

```bash
pip install -r requirements.txt
python examples/list_sessions.py
```

Every script documents its own flags under `--help`.

## Examples

| Script | What it shows |
| --- | --- |
| `examples/list_sessions.py` | List recording sessions with filters, sorting, and pagination |
| `examples/download_outputs.py` | List a session's score CSVs and download them |
| `examples/inject_marker.py` | Stamp a marker into a live recording, untargeted or targeted |
| `examples/realtime.py` | The realtime WebSocket: stream states, live score events, reconnect rules |

## Notes

- The whole `/api/dev` namespace shares a per-IP budget of 300 requests per minute
  with a burst of 60.
- Every non-2xx response body is `{"error": "<code>", "message": "<text>"}`. Branch
  on `error`; the message text is not stable.
- On a group key, reads of other members' data are recorded in an append-only audit
  trail before the response is served.

## License

MIT, see [LICENSE](LICENSE).
