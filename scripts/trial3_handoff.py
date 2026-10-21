"""Wait briefly for one coordinator packet without inspecting any other files."""

import argparse
import json
import time
from pathlib import Path


def wait_packet(path: Path, seconds: float = 25.0) -> dict[str, object]:
    """Read only the named packet, keeping each wait below thirty seconds."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if path.is_file():
            return {"ready": True, "packet": json.loads(path.read_text())}
        time.sleep(0.5)
    return {"ready": False}


def main() -> None:
    """Print the packet or a not-ready result for the worker to retry."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    print(json.dumps(wait_packet(args.packet), ensure_ascii=False))


if __name__ == "__main__":
    main()
