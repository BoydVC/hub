#!/usr/bin/env bash
cd "$(dirname "$0")/.." && ./run.sh >/dev/null && python3 tests/smoke.py
