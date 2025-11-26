#!/bin/bash
# Setup venv for WhisperTux using uv

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Creating venv with uv..."
uv venv .venv

echo "Installing dependencies..."
uv pip install -r requirements.txt

echo "Done! Activate with: source .venv/bin/activate"
