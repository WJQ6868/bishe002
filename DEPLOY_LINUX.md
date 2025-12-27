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

默认会：

- 安装系统依赖：`python3`、`nginx`、`nodejs` 等
- 将代码同步到 `/opt/edu-system`
- 创建 Python venv 并安装 [backend/requirements.txt](backend/requirements.txt)
- 构建前端 `frontend/dist`
- 生成并启动 systemd 服务：`edu-system-backend.service`
- 写入并加载 Nginx 配置：`/etc/nginx/conf.d/edu-system.conf`

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
