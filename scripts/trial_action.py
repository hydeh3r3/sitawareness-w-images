"""Expose only a task action and its result to a subscription trial worker."""

import json
import sys
from pathlib import Path

from veup.subscription import apply_action


def main() -> None:
    """Apply one JSON action; keep private labels out of the worker response."""
    root = Path(sys.argv[1])
    action = json.loads(sys.argv[2])
    print(json.dumps(apply_action(root, action, actor=f"/root/{root.name}")))


if __name__ == "__main__":
    main()
