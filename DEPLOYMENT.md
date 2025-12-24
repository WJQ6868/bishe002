# 高校智能教务系统 - 部署与测试指南

## 📋 快速开始

### 1. 环境要求
- **Python**: 3.10+
- **Node.js**: 16+
- **数据库**: SQLite (已内置)

### 2. 首次部署步骤

#### 方法一: 使用增强版启动脚本 (推荐)
```bash
# Windows 系统
start_project_enhanced.bat
```

脚本会自动:
- ✅ 检查 Python 虚拟环境
- ✅ 提示首次运行时初始化数据库
- ✅ 启动后端和前端服务
- ✅ 打开浏览器
- ✅ 显示测试账号

#### 方法二: 手动部署
```bash
# 1. 后端环境配置
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. 初始化数据库 (仅首次)
python init_db_data.py

# 3. 启动后端服务
python -m uvicorn app.main:socket_app --reload --host 0.0.0.0 --port 8000

# 4. 前端环境配置 (新终端)
cd frontend
npm install

# 5. 启动前端服务
npm run dev
```

### 3. 访问系统
- **前端地址**: http://localhost:2003
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

---

## 🔑 测试账号

| 角色 | 用户名 | 密码 | 说明 |
|------|--------|------|------|
| **管理员** | 800001 | 123456 | 完整系统权限 |
| **教师** | 100001 | 123456 | 教学管理权限 |
| **学生** | 20230001 | 123456 | 学习功能权限 |

---

## 🧪 功能测试清单

### 学生端功能
- [ ] 登录系统 (用户: 20230001)
- [ ] 请假申请 - 提交新申请
- [ ] 请假申请 - 查看历史记录
- [ ] 我的作业 - 查看待完成作业
- [ ] 我的作业 - 提交作业
- [ ] 上课签到 - 输入签到码
- [ ] 上课签到 - 查看签到历史

### 教师端功能
- [ ] 登录系统 (用户: 100001)
- [ ] 上课点名 - 生成二维码
- [ ] 上课点名 - 手动点名
- [ ] 上课点名 - 查看实时统计
- [ ] 作业管理 - 布置作业
- [ ] 作业管理 - 查看提交列表
- [ ] 作业管理 - 批改作业
- [ ] 工作安排 - 查看日程
- [ ] 工作安排 - 提交调课申请
- [ ] 请假审批 - 审核学生申请

### 管理员功能
- [ ] 登录系统 (用户: 800001)
- [ ] 用户管理 - 查看用户列表
- [ ] 用户管理 - 新增用户
- [ ] 调课审批 - 审核调课申请
- [ ] 课程管理 - 查看课程列表
- [ ] 排课管理 - 查看课表

---

## 🐛 已知问题与解决方案

### 问题 1: API 返回 401 Unauthorized
**原因**: 未登录或 token 过期
**解决**: 
1. 点击右上角退出
2. 重新登录系统
3. 确保使用正确的测试账号

### 问题 2: Socket.IO 连接失败 (403)
**状态**: ✅ 已修复
**解决**: 更新了 CORS 配置，现在支持 localhost:2003 和 localhost:5173

### 问题 3: 数据库表不存在
**原因**: 未初始化数据库
**解决**: 
```bash
cd backend
python init_db_data.py
```

### 问题 4: 前端启动报错 "npm.ps1 无法执行"
**原因**: PowerShell 执行策略限制
**解决**: 使用 `start_project_enhanced.bat` 脚本 (已使用 cmd /c 解决)

---

## 📁 项目结构

```
d:\bishe\one\
├── backend/                 # 后端 FastAPI
│   ├── app/
│   │   ├── models/          # 数据模型
│   │   ├── routers/         # API 路由
│   │   ├── schemas/         # 数据验证
│   │   ├── services/        # Socket.IO 服务
│   │   └── main.py          # 应用入口
│   ├── init_db_data.py      # 数据库初始化
│   ├── edu_system.db        # SQLite 数据库
│   └── requirements.txt     # Python 依赖
├── frontend/                # 前端 Vue3
│   ├── src/
│   │   ├── views/           # 页面组件
│   │   │   ├── admin/       # 管理员页面
│   │   │   ├── teacher/     # 教师页面
│   │   │   └── student/     # 学生页面
│   │   ├── router/          # 路由配置
│   │   └── App.vue          # 根组件
│   └── package.json         # Node 依赖
├── start_project.bat        # 标准启动脚本
└── start_project_enhanced.bat  # 增强版启动脚本 (推荐)
```

---

## 🚀 生产部署建议

### 环境变量配置
创建 `backend/.env` 文件:
```env
DATABASE_URL=sqlite:///./edu_system.db
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://your-domain.com
```

### 前端构建
```bash
cd frontend
npm run build
```

### 使用 Docker (可选)
```bash
# 即将支持...
docker-compose up -d
```

---

## 📞 技术支持

如遇问题:
1. 查看 `C:\Users\wangj\.gemini\antigravity\brain\51c651bb-7fcb-4d03-8d1f-d69ac4343feb\bug_report.md`
2. 查看后端日志 (Backend Service 窗口)
3. 查看前端日志 (Frontend Service 窗口 / 浏览器控制台)

---

## 📝 更新日志

### 2025-12-05
- ✅ 完成教学管理功能开发
- ✅ 修复 Socket.IO CORS 配置
- ✅ 创建增强版启动脚本
- ✅ 添加测试数据生成
- ✅ 完成功能测试报告
