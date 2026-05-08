#!/usr/bin/env bash
# Start frontend dev server
set -e
cd "$(dirname "$0")/frontend"
npm install
npm run dev
