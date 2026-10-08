#!/bin/sh
# Re-scrape madewithnestle.ca, rebuild the entity graph, and re-ingest into Azure AI Search.
# Extra args go to scrape.py, e.g. ./scripts/nestle/refresh.sh --max-pages 50
set -e
cd "$(dirname "$0")/../.."

. ./scripts/load_python_env.sh
./.venv/bin/python -m pip --quiet --disable-pip-version-check install playwright

./.venv/bin/python ./scripts/nestle/scrape.py "$@"
./.venv/bin/python ./scripts/nestle/extract_entities.py
./scripts/prepdocs.sh

echo "Index updated. Run 'azd deploy backend' to ship the rebuilt graph to the deployed app."
