#!/bin/bash

uv venv --python 3.12

source .venv/Scripts/activate || source .venv/bin/activate
uv sync --all-extras

pre-commit install

echo ""
echo "Virtual environment created and activated."
echo ""
