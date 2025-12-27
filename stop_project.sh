#!/usr/bin/env bash
set -Eeuo pipefail

# Linux 一键停止脚本（等价于 stop_project.bat）
# - 优先读取 backend.pid/frontend.pid 停止进程
# - 兜底：按端口 8000/2003 查找并停止监听进程
# - 清理 pid 文件

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKEND_PORT="8000"
FRONTEND_PORT="2003"

BACKEND_PID_FILE="${ROOT_DIR}/backend.pid"
FRONTEND_PID_FILE="${ROOT_DIR}/frontend.pid"

have_cmd() { command -v "$1" >/dev/null 2>&1; }

log() {
  printf '%s %s\n' "[${1}]" "${2}"
}

pids_listening_on_port() {
  local port="$1"

  if have_cmd lsof; then
    lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
    return
  fi

  if have_cmd ss; then
    ss -ltnp 2>/dev/null | awk -v p=":${port}" '$4 ~ p {print $NF}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u || true
    return
  fi

  if have_cmd netstat; then
    netstat -ltnp 2>/dev/null | awk -v p=":${port}" '$4 ~ p {print $7}' | sed -n 's#^\([0-9]\+\)/.*#\1#p' | sort -u || true
    return
  fi

  echo ""
}

kill_pid_gracefully() {
  local pid="$1"
  local name="$2"

  if [[ -z "${pid}" ]]; then
    return
  fi

  if ! kill -0 "${pid}" >/dev/null 2>&1; then
    return
  fi

  log "INFO" "停止 ${name} (PID=${pid})..."
  kill "${pid}" >/dev/null 2>&1 || true

  # 等待最多 10 秒
  for _ in {1..10}; do
    if ! kill -0 "${pid}" >/dev/null 2>&1; then
      log "OK" "已停止 ${name} (PID=${pid})"
      return
    fi
    sleep 1
  done

  log "WARN" "${name} 未退出，强制杀死 (PID=${pid})"
  kill -9 "${pid}" >/dev/null 2>&1 || true
}

stop_by_pid_file() {
  local pid_file="$1"
  local name="$2"

  if [[ -f "${pid_file}" ]]; then
    local pid
    pid="$(cat "${pid_file}" 2>/dev/null | tr -d '\r' || true)"
    kill_pid_gracefully "${pid}" "${name}"
    rm -f "${pid_file}" || true
  fi
}

stop_by_port() {
  local port="$1"
  local name="$2"
  local pids

  pids="$(pids_listening_on_port "${port}" | tr -d '\r' | tr '\n' ' ')"
  if [[ -z "${pids// }" ]]; then
    return
  fi

  for pid in ${pids}; do
    kill_pid_gracefully "${pid}" "${name}@:${port}"
  done
}

main() {
  echo "======================================================="
  echo "      正在停止高校智能教务系统 (Smart University System)"
  echo "======================================================="

  log "1/2" "正在停止后端服务 (Port ${BACKEND_PORT})..."
  stop_by_pid_file "${BACKEND_PID_FILE}" "Backend"
  stop_by_port "${BACKEND_PORT}" "Backend"

  log "2/2" "正在停止前端服务 (Port ${FRONTEND_PORT})..."
  stop_by_pid_file "${FRONTEND_PID_FILE}" "Frontend"
  stop_by_port "${FRONTEND_PORT}" "Frontend"

  echo "======================================================="
  echo "系统已停止！"
  echo "======================================================="
}

main "$@"
