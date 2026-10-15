#!/bin/sh
# Starts TerminalTanks with the first Python 3.10+ it can find.
cd "$(dirname "$0")" || exit 1
for py in python3 python; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    exec "$py" terminaltanks.py "$@"
  fi
done
echo "Python 3.10 or newer was not found." >&2
echo "Install it from https://www.python.org/downloads/ and run this again." >&2
exit 1
