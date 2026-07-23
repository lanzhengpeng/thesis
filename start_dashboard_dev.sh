#!/bin/bash
cd /Users/lanzhengpeng/develop/thesis/paas_dashboard
PORT="${1:-${PORT:-5174}}"
VITE_API_BASE_URL="" npm run dev -- --host --port "$PORT"
