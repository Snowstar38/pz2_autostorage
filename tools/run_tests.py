"""Run the source-only Python and Node checks without silently skipping either."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", default="node", help="Node.js executable or absolute path")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    node = shutil.which(args.node)
    if not node:
        parser.error("Node.js is required; install it or pass --node <executable>")
    tests = sorted((root / "tests").glob("test_*.py"))
    scripts = sorted((root / "tests").glob("test_*.mjs"))
    if not tests or not scripts:
        raise SystemExit("Expected both Python and Node test suites")
    for executable, paths in ((sys.executable, tests), (node, scripts)):
        for path in paths:
            print(f"Running {path.name}", flush=True)
            subprocess.run([executable, str(path)], cwd=root, check=True)
    print(f"Passed {len(tests)} Python and {len(scripts)} Node checks")


if __name__ == "__main__":
    main()
