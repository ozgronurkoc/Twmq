#!/bin/bash
set -e

# Install/sync Python dependencies (including the local package)
uv sync --extra test
