#!/usr/bin/env bash
set -e

echo "Updating system packages..."
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt
pip install -r requirements-dev.txt

echo "Running tests..."
pytest -q

echo "Done."
