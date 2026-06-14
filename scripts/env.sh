#!/bin/bash

uv venv

source .venv/Scripts/activate || source .venv/bin/activate
uv sync --all-extras

pre-commit install

echo ""
echo "Virtual environment created and activated."
echo ""
