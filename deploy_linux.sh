#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="edu-system"
APP_DIR="/opt/${APP_NAME}"
APP_USER="${APP_NAME}"
BACKEND_PORT="8000"
NGINX_CONF_PATH="/etc/nginx/conf.d/${APP_NAME}.conf"

usage() {
  cat <<'EOF'
用法:
  sudo ./deploy_linux.sh [--app-dir /opt/edu-system] [--domain example.com]

说明:
  - 适用于全新 Linux 服务器的一键部署脚本（FastAPI + Vite/Vue 前端 + Nginx + systemd）
  - 默认把项目安装到 /opt/edu-system
  - 需要你先把本仓库代码上传/同步到服务器，并在仓库根目录执行此脚本

可选参数:
  --app-dir   安装目录（默认 /opt/edu-system）
  --domain    Nginx server_name（可传多个，用空格分隔并加引号；默认自动探测本机主 IP/hostname）

示例:
  sudo ./deploy_linux.sh --domain "wangjiaqi.me 47.98.128.206"
EOF
}

# 为空表示未指定：后续会自动探测本机主 IP/hostname
DOMAIN=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-dir)
      APP_DIR="$2"; shift 2 ;;
    --domain)
      DOMAIN="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "未知参数: $1" >&2
      usage
      exit 2
      ;;
  esac
done

# 尽量避免 nginx `server_name _` 与系统默认站点冲突。
# 若用户未显式传 --domain，则自动使用服务器主 IP（取不到则用 hostname）。
if [[ -z "${DOMAIN}" ]]; then
  if have_cmd hostname; then
    DOMAIN="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
    if [[ -z "${DOMAIN}" ]]; then
      DOMAIN="$(hostname 2>/dev/null || true)"
    fi
  fi
  DOMAIN="${DOMAIN:-_}"
fi

if [[ "${DOMAIN}" == "_" ]]; then
  echo "[WARN] 未能自动探测到可用的 server_name，将使用 '_'。" >&2
  echo "[WARN] 这可能与系统默认站点冲突，导致访问域名仍显示 Welcome to nginx。" >&2
  echo "[WARN] 建议显式指定：--domain \"你的域名 你的服务器IP\"" >&2
fi

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "请用 root 运行（建议 sudo）。" >&2
    exit 1
  fi
}

have_cmd() { command -v "$1" >/dev/null 2>&1; }

detect_pkg_mgr() {
  if have_cmd apt-get; then echo "apt"; return; fi
  if have_cmd dnf; then echo "dnf"; return; fi
  if have_cmd yum; then echo "yum"; return; fi
  echo "unknown"
}

install_packages() {
  local mgr
  mgr="$(detect_pkg_mgr)"
  echo "[1/8] 安装系统依赖（pkg mgr: ${mgr}）..."

  if [[ "${mgr}" == "apt" ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y --no-install-recommends \
      ca-certificates curl git rsync nginx \
      python3 python3-venv python3-pip python3-dev \
      build-essential pkg-config \
      libjpeg-dev zlib1g-dev libffi-dev
  elif [[ "${mgr}" == "dnf" || "${mgr}" == "yum" ]]; then
    ${mgr} makecache -y || true
    ${mgr} install -y \
      ca-certificates curl git rsync nginx \
      python3 python3-pip python3-devel \
      gcc gcc-c++ make pkgconfig \
      libjpeg-turbo-devel zlib-devel libffi-devel
  else
    echo "不支持的包管理器（需要 apt/dnf/yum）。" >&2
    exit 1
  fi
}

install_node() {
  echo "[2/8] 安装 Node.js 20 LTS..."
  if have_cmd node && have_cmd npm; then
    local ver
    ver="$(node -v || true)"
    echo "已检测到 node: ${ver}，跳过安装。"
    return
  fi

  local mgr
  mgr="$(detect_pkg_mgr)"
  if [[ "${mgr}" == "apt" ]]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
  elif [[ "${mgr}" == "dnf" || "${mgr}" == "yum" ]]; then
    curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
    ${mgr} install -y nodejs
  else
    echo "无法自动安装 Node.js（未知包管理器）。" >&2
    exit 1
  fi
}

validate_repo_layout() {
  echo "[3/8] 校验项目目录结构..."
  if [[ ! -d "backend" || ! -d "frontend" ]]; then
    echo "请在仓库根目录执行此脚本（需包含 backend/ 与 frontend/）。" >&2
    exit 1
  fi
  if [[ ! -f "backend/requirements.txt" ]]; then
    echo "未找到 backend/requirements.txt。" >&2
    exit 1
  fi
  if [[ ! -f "frontend/package.json" ]]; then
    echo "未找到 frontend/package.json。" >&2
    exit 1
  fi
}

ensure_user_and_dirs() {
  echo "[4/8] 创建运行用户与部署目录..."
  if ! id -u "${APP_USER}" >/dev/null 2>&1; then
    useradd --system --create-home --shell /bin/bash "${APP_USER}"
  fi

  mkdir -p "${APP_DIR}"
  chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
}

sync_code() {
  echo "[5/8] 同步代码到 ${APP_DIR}..."
  # 排除体积大/无用目录（避免污染服务器）
  rsync -a --delete \
    --exclude ".git" \
    --exclude "**/node_modules" \
    --exclude "**/.venv" \
    --exclude "**/venv" \
    --exclude "**/__pycache__" \
    --exclude "backend/Lib" \
    --exclude "backend/Include" \
    --exclude "backend/Scripts" \
    --exclude "backend/*.pid" \
    ./ "${APP_DIR}/"

  chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
}

setup_python_venv() {
  echo "[6/8] 安装后端 Python 依赖（venv: ${APP_DIR}/.venv）..."
  python3 -m venv "${APP_DIR}/.venv"
  "${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip wheel
  "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/backend/requirements.txt"

  # 确保上传目录可写
  mkdir -p "${APP_DIR}/backend/static/uploads"
  chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}/backend/static/uploads"
}

build_frontend() {
  echo "[7/8] 构建前端（Vite dist）..."
  pushd "${APP_DIR}/frontend" >/dev/null
  # 说明：puppeteer 默认会在 npm install 阶段下载 Chromium。
  # 部分服务器网络环境会导致下载失败（ECONNRESET），从而中断部署。
  # 本项目运行时不依赖该浏览器文件，因此默认跳过下载以提高部署成功率。
  PUPPETEER_SKIP_DOWNLOAD=1 npm install
  PUPPETEER_SKIP_DOWNLOAD=1 npm run build:no-check
  popd >/dev/null
}

write_backend_env_if_missing() {
  local env_file
  env_file="${APP_DIR}/backend/.env"
  if [[ -f "${env_file}" ]]; then
    return
  fi
  echo "生成 ${env_file}（可按需修改）..."
  local secret
  if have_cmd openssl; then
    secret="$(openssl rand -hex 32)"
  else
    secret="change-me-please"
  fi
  cat >"${env_file}" <<EOF
# 后端运行配置（systemd 会加载此文件）
SECRET_KEY=${secret}
# 如需启用 AI 功能，请填写你的 key
DASHSCOPE_API_KEY=
# Redis 当前为可选依赖（未部署也可启动），需要的话改成你的地址
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
EOF
  chown "${APP_USER}:${APP_USER}" "${env_file}"
  chmod 600 "${env_file}"
}

write_systemd_unit() {
  echo "[8/8] 写入 systemd 服务与 Nginx 配置并启动..."

  cat >/etc/systemd/system/${APP_NAME}-backend.service <<EOF
[Unit]
Description=${APP_NAME} FastAPI Backend
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}/backend
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-${APP_DIR}/backend/.env
ExecStart=${APP_DIR}/.venv/bin/python -m uvicorn app.main:socket_app --host 127.0.0.1 --port ${BACKEND_PORT} --proxy-headers --forwarded-allow-ips='*'
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable --now ${APP_NAME}-backend.service

  # Nginx：禁用系统默认站点（避免访问域名时仍显示 Welcome to nginx）
  # Ubuntu/Debian 常见：/etc/nginx/sites-enabled/default
  if [[ -e "/etc/nginx/sites-enabled/default" ]]; then
    rm -f "/etc/nginx/sites-enabled/default"
  fi
  # CentOS/RHEL 系常见：/etc/nginx/conf.d/default.conf
  if [[ -e "/etc/nginx/conf.d/default.conf" ]]; then
    mv -f "/etc/nginx/conf.d/default.conf" "/etc/nginx/conf.d/default.conf.bak" || true
  fi

  # Nginx
  cat >"${NGINX_CONF_PATH}" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    client_max_body_size 50m;

    root ${APP_DIR}/frontend/dist;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # FastAPI APIs（后端自身就有 /api 前缀，无需 rewrite）
    location /api/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # FastAPI 静态资源（/static）
    location /static/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_set_header Host \$host;
    }

    # Socket.IO（WebSocket Upgrade）
    location /socket.io/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 3600;
    }
}
EOF

  nginx -t
  systemctl enable --now nginx
  systemctl reload nginx

  echo "\n部署完成："
  echo "- Nginx server_name: ${DOMAIN}"
  echo "- 直连后端健康检查:  curl -fsS http://127.0.0.1:${BACKEND_PORT}/api/health"
  echo "- 直连后端 Socket.IO 状态: curl -fsS http://127.0.0.1:${BACKEND_PORT}/api/socketio/status"
  echo "- 通过 Nginx 健康检查:     curl -fsS http://127.0.0.1/api/health"
  echo "- 打开浏览器访问:  http://<你的服务器IP>/"
  echo "\n常用命令："
  echo "- 查看后端日志: journalctl -u ${APP_NAME}-backend -f"
  echo "- 重启后端:     systemctl restart ${APP_NAME}-backend"
}

main() {
  require_root
  validate_repo_layout
  install_packages
  install_node
  ensure_user_and_dirs
  sync_code
  setup_python_venv
  build_frontend
  write_backend_env_if_missing
  write_systemd_unit
}

main "$@"
