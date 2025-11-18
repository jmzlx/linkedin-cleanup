#!/bin/bash
# Wrapper script for extract_search_results.py
# Loads .env file and runs Python with unbuffered output

# Get the project root (directory containing this script)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"

# Load .env file if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Ensure PYTHONUNBUFFERED is set (from .env or default)
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

# Run the Python script with uv run to use project dependencies
# The -u flag ensures unbuffered output
cd "$PROJECT_ROOT"
exec uv run python -u "$SCRIPTS_DIR/extract_search_results.py" "$@"

