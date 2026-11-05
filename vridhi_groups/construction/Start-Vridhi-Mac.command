#!/bin/zsh
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 1

for candidate in python3 python3.14 python3.13 python3.12; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; sys.exit(not ((3,12) <= sys.version_info[:2] < (3,15)))' >/dev/null 2>&1; then
    "$candidate" "$ROOT/scripts/bootstrap.py" "$@"
    result=$?
    if [[ $# == 0 ]]; then
      read -r "?Press Return to close this window..."
    fi
    exit "$result"
  fi
done
print -u2 "Install Python 3.12, 3.13 or 3.14 from python.org, then run Start-Vridhi-Mac.command again."
read -r "?Press Return to close this window..."
exit 1
