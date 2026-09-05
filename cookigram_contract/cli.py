from __future__ import annotations

import argparse
from pathlib import Path

from .contract import content_sha, validate_content, verify_output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cookigram-contract")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("root", type=Path)
    validate.add_argument("--allow-empty", action="store_true")
    hash_cmd = sub.add_parser("hash")
    hash_cmd.add_argument("root", type=Path)
    output = sub.add_parser("verify-output")
    output.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "hash":
        print(content_sha(args.root))
        return 0
    errors = validate_content(args.root, args.allow_empty) if args.command == "validate" else verify_output(args.output)
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print("OK")
    return 0
