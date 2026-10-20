"""Worker-visible action bridge for Trial 2, including its timed scenario update."""

import json
import sys
from pathlib import Path

from veup.trial2 import action


def main() -> None:
    """Apply one worker action and print only the visible task result."""
    root = Path(sys.argv[1])
    print(json.dumps(action(root, json.loads(sys.argv[2]), f"/root/t2_subject_{root.name}")))


if __name__ == "__main__":
    main()
