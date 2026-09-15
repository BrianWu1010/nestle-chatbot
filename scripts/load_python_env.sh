#!/bin/sh

python_cmd=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    ver="$("$candidate" -c 'import sys; print("%d.%d" % (sys.version_info.major, sys.version_info.minor))')"
    major="${ver%%.*}"
    minor="${ver#*.}"
    if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; }; then
      python_cmd="$candidate"
      break
    fi
  fi
done

if [ -z "$python_cmd" ]; then
  echo "Python 3.10 or later is required. This machine's python3 is too old for aiohttp==3.14.1."
  echo "Install Python 3.10+ (for example: brew install python@3.12) and retry."
  exit 1
fi

echo "Creating Python virtual environment \".venv\" with $python_cmd..."
"$python_cmd" -m venv .venv

echo 'Installing dependencies from "requirements.txt" into virtual environment (in quiet mode)...'
.venv/bin/python -m pip --quiet --disable-pip-version-check install -r app/backend/requirements.txt
