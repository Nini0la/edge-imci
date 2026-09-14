"""Launch the authorized Azure demo using a resource key held only in memory.

Requires an existing Azure CLI login with permission to read this resource's
keys. Does not print, persist, rotate, or pass the key through command arguments.
The normal app CLI also supports environment credentials or Azure CLI identity.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--env-file", type=Path, default=root / ".env")
    args = parser.parse_args()
    try:
        response = subprocess.run(
            ["az", "cognitiveservices", "account", "keys", "list",
             "--resource-group", "synthetic-data-generation", "--name", "openai-sota",
             "--query", "key1", "--output", "tsv", "--only-show-errors"],
            capture_output=True, text=True, timeout=30, check=True,
        )
        key = response.stdout.strip()
        if not key or any(character.isspace() for character in key):
            raise ValueError("Invalid credential response")
    except (OSError, subprocess.SubprocessError, ValueError):
        print("Could not obtain the authorized Azure resource credential. Check Azure CLI login and resource-key permissions.", file=sys.stderr)
        return 1
    environment = {
        **os.environ,
        "EDGEIMCI_FRONTIER_API_KEY": key,
        "EDGEIMCI_FRONTIER_ENDPOINT": "https://openai-sota.openai.azure.com/",
        "EDGEIMCI_FRONTIER_MODEL": "gpt-5.2",
        "PYTHONPATH": os.pathsep.join((str(root / "src"), str(root))),
        "PYTHONUNBUFFERED": "1",
    }
    env_file = args.env_file.resolve()
    os.chdir(root)
    os.execve(sys.executable, [
        sys.executable, "-m", "app", "--extractor", "modal",
        "--language-understanding", "frontier", "--port", str(args.port),
        "--env-file", str(env_file),
    ], environment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
