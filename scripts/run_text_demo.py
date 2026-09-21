"""Launch the text-only demo without speech credentials."""

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
    parser.add_argument("--static-root", type=Path, default=root / "web" / "dist")
    args = parser.parse_args()
    if not os.environ.get("EDGEIMCI_FRONTIER_API_KEY"):
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
            print("Could not obtain the authorized text-processing credential. Check Azure CLI login and resource-key permissions.", file=sys.stderr)
            return 1
        os.environ["EDGEIMCI_FRONTIER_API_KEY"] = key
    os.environ.setdefault("EDGEIMCI_FRONTIER_ENDPOINT", "https://openai-sota.openai.azure.com/")
    os.environ.setdefault("EDGEIMCI_FRONTIER_MODEL", "gpt-5.2")
    sys.path[:0] = [str(root / "src"), str(root)]
    from app.api import make_server

    server = make_server(port=args.port, static_root=args.static_root.resolve(),
                         extractor_mode="modal", language_understanding_mode="frontier")
    print(f"EdgeIMCI text assessment available at http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
