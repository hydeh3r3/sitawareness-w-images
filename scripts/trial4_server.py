"""Local ops API for Trial 4 workers; state and logs stay in the coordinator's study folder."""

import argparse
import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from veup import trial4

LOCK = threading.Lock()


def append_event(path: Path, event: dict[str, Any]) -> None:
    """Append one hash-chained event; the chain catches edits and tail loss."""
    previous = "0" * 64
    if path.exists() and path.stat().st_size:
        previous = json.loads(path.read_text().splitlines()[-1])["hash"]
    body = json.dumps(event | {"prev": previous}, sort_keys=True, ensure_ascii=False)
    record = json.loads(body) | {"hash": hashlib.sha256(body.encode()).hexdigest()}
    with path.open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def serve_request(root: Path, token: str, tool: str, arg: Any) -> dict[str, Any]:
    """Load one run by token, apply the request, and persist state and events."""
    registry = json.loads((root / "private/registry.json").read_text())
    run = registry.get(token)
    if run is None:
        return {"error": "unauthorized"}
    private = root / "runs" / run / "private"
    state_path = private / "session.json"
    session = (
        trial4.Session.model_validate_json(state_path.read_text())
        if state_path.exists()
        else trial4.new_session()
    )
    updated, reply, cost = trial4.handle(session, tool, arg)
    kind = "call" if cost else ("finish" if tool == "finish" and updated.finished else "free")
    append_event(
        private / "events.jsonl", {"kind": kind, "tool": tool, "arg": arg, "result": reply}
    )
    state_path.write_text(updated.model_dump_json(indent=2))
    return reply


def handler_for(root: Path) -> type[BaseHTTPRequestHandler]:
    """Bind the request handler to one study folder."""

    class Handler(BaseHTTPRequestHandler):
        """Accept POST /ops only."""

        def do_POST(self) -> None:
            """Handle one ops request."""
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(min(length, 200_000)) or b"{}")
                with LOCK:
                    reply = serve_request(
                        root,
                        self.headers.get("X-Ops-Token", ""),
                        str(body.get("tool")),
                        body.get("arg"),
                    )
                code = 401 if reply.get("error") == "unauthorized" else 200
            except (ValueError, OSError) as error:
                reply, code = {"error": f"bad request: {error}"}, 400
            data = json.dumps(reply, indent=2).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_: Any) -> None:
            """Keep the coordinator console quiet."""

    return Handler


def main() -> None:
    """Serve until stopped."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--port", type=int, default=8747)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(args.root.resolve()))
    print(f"serving {args.root} on 127.0.0.1:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
