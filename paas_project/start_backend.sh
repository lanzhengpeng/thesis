#!/bin/bash
# 启动后端服务（使用 conda thesis 环境）
# 用法：
#   ./start_backend.sh                  # 同时启动系统口 8000 + 服务口 8001
#   ./start_backend.sh --mode system    # 仅启动系统口
#   ./start_backend.sh --mode service   # 仅启动服务口

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

conda run -n thesis python main.py "$@"
