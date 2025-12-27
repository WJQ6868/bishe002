# Linux 服务器部署（全新机器）

这份项目后端为 FastAPI（Uvicorn），前端为 Vite/Vue，数据库默认使用 SQLite（会自动创建表并写入默认账号）。

## 0. 前置条件

- 一台全新 Linux 服务器（建议 Ubuntu 22.04/24.04 或 CentOS/RHEL 兼容发行版）
- 你能以 `root` 或 `sudo` 权限执行命令
- 你已把本仓库上传到服务器（例如 `scp`/`rsync`/`git clone`）

## 1. 一键部署

在仓库根目录执行：

```bash
chmod +x deploy_linux.sh
sudo ./deploy_linux.sh --domain <你的域名或IP>
```

如果你希望域名和服务器 IP 都能访问到同一套站点，可以一次写多个 `server_name`（用空格分隔并加引号）：

```bash
sudo ./deploy_linux.sh --domain "wangjiaqi.me 47.98.128.206"
```

默认会：

- 安装系统依赖：`python3`、`nginx`、`nodejs` 等
- 将代码同步到 `/opt/edu-system`
- 创建 Python venv 并安装 [backend/requirements.txt](backend/requirements.txt)
- 构建前端 `frontend/dist`
- 生成并启动 systemd 服务：`edu-system-backend.service`
- 写入并加载 Nginx 配置：`/etc/nginx/conf.d/edu-system.conf`

## 1.5 更新代码（git 拉取最新）

如果你的服务器上已存在仓库目录（例如你图里是：`/root/one-liunx/bishe002`），可以使用仓库根目录自带脚本一键拉取最新代码：

```bash
chmod +x pull_github_updates.sh
./pull_github_updates.sh --dir /root/one-liunx/bishe002
```

说明：

- 默认“安全模式”：检测到本地改动会退出，避免误覆盖。
- 如需强制与远程一致（会覆盖本地改动）：

```bash
./pull_github_updates.sh --dir /root/one-liunx/bishe002 --force
```

## 2. 验证

```bash
curl -fsS http://127.0.0.1/api/health
curl -fsS http://127.0.0.1/api/socketio/status
```

浏览器访问：

- `http://<服务器IP>/`

## 3. 默认测试账号

- 管理员：800001 / 123456
- 教师：100001 / 123456
- 学生：20230001 / 123456

## 4. 运维命令

```bash
# 查看后端状态
systemctl status edu-system-backend

# 查看后端日志
journalctl -u edu-system-backend -f

# 重启后端
systemctl restart edu-system-backend

# 检查 nginx 配置
nginx -t

# 重载 nginx
systemctl reload nginx
```

## 5. 配置项（可选）

后端环境变量文件：`/opt/edu-system/backend/.env`

- `SECRET_KEY`：JWT/鉴权相关（脚本会自动生成）
- `DASHSCOPE_API_KEY`：AI 功能用（没有也能启动）
- `REDIS_*`：Redis 目前为可选（未部署也能启动）

## 常见问题

### npm install 报 puppeteer 下载 Chrome 失败（ECONNRESET）

部分服务器网络环境会导致 puppeteer 在安装阶段下载 Chromium 失败，从而中断前端构建。

解决（跳过下载）：

```bash
cd /opt/edu-system/frontend
PUPPETEER_SKIP_DOWNLOAD=1 npm install
PUPPETEER_SKIP_DOWNLOAD=1 npm run build:no-check
```

### /api/health 返回 404，但后端日志显示 8000 已启动

如果你看到类似警告：`nginx: [warn] conflicting server name "_" on 0.0.0.0:80, ignored`，通常表示你的 Nginx 有多个 `server_name _;` 的站点配置冲突，导致本项目的 server 块被忽略，从而 `/api/*` 没有被反代到后端。

排查：

```bash
# 直连后端（确认 FastAPI 正常）
curl -fsS http://127.0.0.1:8000/api/health

# 走 Nginx（确认反代正常）
curl -fsS http://127.0.0.1/api/health
```

解决（推荐）：部署时指定你的域名或服务器 IP：

```bash
sudo ./deploy_linux.sh --domain <你的域名或服务器IP>
```

或手动修改 Nginx 配置 `server_name` 后重载：

```bash
nginx -t
sudo systemctl reload nginx
```
