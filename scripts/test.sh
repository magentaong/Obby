#!/usr/bin/env sh
set -eu

python -m compileall obby.py obby_core
python -m unittest discover -s tests
