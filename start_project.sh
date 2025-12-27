#!/usr/bin/env bash
set -Eeuo pipefail

# Linux 一键启动脚本（等价于 start_project.bat）
# - 后端：FastAPI + Socket.IO (uvicorn) 端口 8000
# - 前端：Vite dev server 端口 2003
# - 写入：backend.pid / frontend.pid
# - 日志：backend.log / frontend.log

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"

BACKEND_PORT="8000"
FRONTEND_PORT="2003"

BACKEND_PID_FILE="${ROOT_DIR}/backend.pid"
FRONTEND_PID_FILE="${ROOT_DIR}/frontend.pid"
BACKEND_LOG_FILE="${ROOT_DIR}/backend.log"
FRONTEND_LOG_FILE="${ROOT_DIR}/frontend.log"

log() {
  printf '%s %s\n' "[${1}]" "${2}"
}

have_cmd() { command -v "$1" >/dev/null 2>&1; }

pick_python() {
  if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
    echo "${ROOT_DIR}/.venv/bin/python"; return
  fi
  if [[ -x "${BACKEND_DIR}/venv/bin/python" ]]; then
    echo "${BACKEND_DIR}/venv/bin/python"; return
  fi
  if have_cmd python3; then
    echo "python3"; return
  fi
  if have_cmd python; then
    echo "python"; return
  fi
  echo ""; return
}

pids_listening_on_port() {
  local port="$1"

  if have_cmd lsof; then
    # 输出可能为空
    lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
    return
  fi

  if have_cmd ss; then
    # 解析 ss 输出里的 pid=xxx
    ss -ltnp 2>/dev/null | awk -v p=":${port}" '$4 ~ p {print $NF}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u || true
    return
  fi

  if have_cmd netstat; then
    # netstat -ltnp: 最后一列可能是 pid/program
    netstat -ltnp 2>/dev/null | awk -v p=":${port}" '$4 ~ p {print $7}' | sed -n 's#^\([0-9]\+\)/.*#\1#p' | sort -u || true
    return
  fi

  echo ""
}

is_port_in_use() {
  local port="$1"
  local pids
  pids="$(pids_listening_on_port "${port}" | tr -d '\r' | tr '\n' ' ')"
  [[ -n "${pids// }" ]]
}

start_backend() {
  log "1/3" "正在启动后端服务 (FastAPI + Socket.IO)..."

  if is_port_in_use "${BACKEND_PORT}"; then
    log "WARN" "端口 ${BACKEND_PORT} 已被占用，跳过启动后端。"
    return
  fi

  local py
  py="$(pick_python)"
  [[ -n "${py}" ]] || { echo "ERROR: 未找到 Python（python3/python）。" >&2; exit 1; }

  if [[ ! -d "${BACKEND_DIR}" ]]; then
    echo "ERROR: 未找到 backend 目录：${BACKEND_DIR}" >&2
    exit 1
  fi

  # 简单检查 uvicorn 是否可用
  if ! "${py}" -c "import uvicorn" >/dev/null 2>&1; then
    echo "ERROR: 当前 Python 环境缺少 uvicorn。请先安装后端依赖：" >&2
    echo "  cd backend && pip install -r requirements.txt" >&2
    exit 1
  fi

  (
    cd "${BACKEND_DIR}"
    # 使用 --reload 与 Windows 脚本保持一致
    nohup "${py}" -m uvicorn app.main:socket_app --reload --host 0.0.0.0 --port "${BACKEND_PORT}" >>"${BACKEND_LOG_FILE}" 2>&1 &
    echo $! >"${BACKEND_PID_FILE}"
  )

  log "OK" "后端已启动，PID=$(cat "${BACKEND_PID_FILE}" 2>/dev/null || echo '?')，日志：${BACKEND_LOG_FILE}"
}

start_frontend() {
  log "2/3" "正在启动前端服务 (Vite)..."

  if is_port_in_use "${FRONTEND_PORT}"; then
    log "WARN" "端口 ${FRONTEND_PORT} 已被占用，跳过启动前端。"
    return
  fi

  if [[ ! -d "${FRONTEND_DIR}" ]]; then
    echo "ERROR: 未找到 frontend 目录：${FRONTEND_DIR}" >&2
    exit 1
  fi

  if ! have_cmd npm; then
    echo "ERROR: 未找到 npm，请先安装 Node.js。" >&2
    exit 1
  fi

  # 若 node_modules 不存在则安装（并跳过 puppeteer 下载，避免服务器网络导致失败）
  if [[ ! -d "${FRONTEND_DIR}/node_modules" ]]; then
    log "INFO" "检测到 frontend/node_modules 不存在，先执行 npm install..."
    (
      cd "${FRONTEND_DIR}"
      PUPPETEER_SKIP_DOWNLOAD=1 npm install >>"${FRONTEND_LOG_FILE}" 2>&1
    )
  fi

  (
    cd "${FRONTEND_DIR}"
    nohup npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}" --strictPort >>"${FRONTEND_LOG_FILE}" 2>&1 &
    echo $! >"${FRONTEND_PID_FILE}"
  )

  log "OK" "前端已启动，PID=$(cat "${FRONTEND_PID_FILE}" 2>/dev/null || echo '?')，日志：${FRONTEND_LOG_FILE}"
}

open_browser_if_possible() {
  local url="http://localhost:${FRONTEND_PORT}"
  log "3/3" "等待服务就绪..."
  sleep 2

  echo "======================================================="
  echo "系统启动成功！"
  echo "前端地址: ${url}"
  echo "后端地址: http://localhost:${BACKEND_PORT}"
  echo "日志文件: ${BACKEND_LOG_FILE} / ${FRONTEND_LOG_FILE}"
  echo "======================================================="

  # 在有图形环境时尝试打开浏览器（服务器通常没有 GUI，会自动跳过）
  if [[ -n "${DISPLAY:-}" ]] && have_cmd xdg-open; then
    xdg-open "${url}" >/dev/null 2>&1 || true
  fi
}

main() {
  start_backend
  start_frontend
  open_browser_if_possible
}

main "$@"
