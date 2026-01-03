<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import axios from 'axios'
import { User, Lock, ArrowRight, School, Monitor, Cpu, ChatDotRound } from '@element-plus/icons-vue'

interface LoginForm {
  account: string
  password: string
  role: 'student' | 'teacher' | 'admin'
}

const formRef = ref<FormInstance>()
const loading = ref(false)
const router = useRouter()

const form = reactive<LoginForm>({
  account: '',
  password: '',
  role: 'student'
})

const systemName = ref('高校智能教务系统')

const validateAccount = (_rule: any, value: string, callback: any) => {
  if (value === '') {
    callback(new Error('请输入账号'))
    return
  }

  if (form.role === 'student') {
    if (!/^\d{8}$/.test(value)) {
      callback(new Error('学生账号需为8位数字'))
      return
    }
    if (!value.startsWith('2')) {
      callback(new Error('学生账号应以2开头'))
      return
    }
  } else if (form.role === 'teacher') {
    if (!/^\d{6}$/.test(value)) {
      callback(new Error('教师账号需为6位数字'))
      return
    }
    if (!value.startsWith('1')) {
      callback(new Error('教师账号应以1开头'))
      return
    }
  } else if (form.role === 'admin') {
    if (!/^\d{6}$/.test(value)) {
      callback(new Error('管理员账号需为6位数字'))
      return
    }
    if (!value.startsWith('8')) {
      callback(new Error('管理员账号应以8开头'))
      return
    }
  }

  callback()
}

const rules = reactive<FormRules>({
  account: [{ validator: validateAccount, trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
})

const accountPlaceholder = computed(() => {
  if (form.role === 'student') {
    return '学号（8位，以2开头）'
  }
  if (form.role === 'teacher') {
    return '工号（6位，以1开头）'
  }
  return '工号（6位，以8开头）'
})

const handleLogin = async (formEl: FormInstance | undefined) => {
  if (!formEl) return

  await formEl.validate(async (valid) => {
    if (!valid) return
    loading.value = true

    try {
      const response = await axios.post('/token', {
        username: form.account,
        password: form.password,
        role: form.role
      })
      const { access_token } = response.data

      localStorage.setItem('token', access_token)
      axios.defaults.baseURL = import.meta.env.VITE_API_BASE_URL || '/api'
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

      const profileRes = await axios.get('/auth/me')
      const profile = profileRes.data

      localStorage.setItem('user_role', profile.role)
      localStorage.setItem('user_account', profile.username)
      localStorage.setItem('user_id', String(profile.id))
      localStorage.setItem('user_name', profile.name || profile.username)
      localStorage.setItem('is_login', 'true')

      const actualRole = profile.role as 'student' | 'teacher' | 'admin'
      ElMessage.success({
        message: `登录成功，欢迎回来，${getRoleName(actualRole)}`,
        type: 'success'
      })

      if (actualRole === 'student') {
        router.push('/student/course-select')
      } else if (actualRole === 'teacher') {
        router.push('/teacher/grade-management')
      } else {
        router.push('/dashboard')
      }
    } catch (error) {
      console.error('Login error:', error)
      ElMessage.error('登录失败，请检查账号密码')
    } finally {
      loading.value = false
    }
  })
}

const getRoleName = (role: string) => {
  const map: Record<string, string> = {
    student: '同学',
    teacher: '老师',
    admin: '管理员'
  }
  return map[role] || ''
}

const handleRoleChange = () => {
  formRef.value?.clearValidate()
}
</script>

<template>
  <div class="ai-login-container">
    <!-- 顶部系统标题�?-->
    <div class="top-bar">
      <div class="top-bar-content">
        <div class="system-logo">
          <el-icon class="logo-icon"><Cpu /></el-icon>
          <span>{{ systemName }}</span>
        </div>
        <div class="system-en">SMART ACADEMIC SYSTEM</div>
      </div>
    </div>

    <!-- 背景装饰 -->
    <div class="tech-grid"></div>
    <div class="glow-orb orb-1"></div>
    <div class="glow-orb orb-2"></div>
    <div class="scan-line"></div>

    <!-- 左侧聊天面板：学�?-->
    <div class="side-panel left-panel">
      <div class="panel-header">
        <el-icon><User /></el-icon>
        <span>学生 / STUDENT</span>
      </div>
      <div class="chat-content">
        <!-- 学生提问 -->
        <div class="chat-row student-row anim-fade-in">
          <div class="avatar-icon student-avatar">
            <el-icon><User /></el-icon>
          </div>
          <div class="bubble student-bubble">
            怎么请假啊？
          </div>
        </div>
        
        <!-- AI 回复 1 -->
        <div class="chat-row ai-row anim-slide-1">
          <div class="bubble ai-bubble">
            请假、销假别慌张，AI 客服来帮�?
          </div>
          <div class="avatar-icon ai-avatar">
            <el-icon><Cpu /></el-icon>
          </div>
        </div>

        <!-- AI 回复 2 -->
        <div class="chat-row ai-row anim-slide-2">
          <div class="bubble ai-bubble">
            线上提交一键审核，无需跑腿教务�?
          </div>
          <div class="avatar-icon ai-avatar">
            <el-icon><Cpu /></el-icon>
          </div>
        </div>

        <!-- AI 回复 3 -->
        <div class="chat-row ai-row anim-slide-3 anim-blink">
          <div class="bubble ai-bubble">
            审批进度实时提醒，销假自动同步超省心
          </div>
          <div class="avatar-icon ai-avatar">
            <el-icon><Cpu /></el-icon>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 核心交互区域 (中间) -->
    <div class="interaction-box">
      <!-- 登录表单�?(底层) -->
      <div class="login-form-layer">
        <div class="form-header">
          <h3>登录</h3>
          <p>Smart Academic System</p>
        </div>
        
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          class="login-form"
          size="large"
        >
          <el-form-item prop="role" class="role-select">
                        <el-radio-group v-model="form.role" @change="handleRoleChange" fill="#00f2fe">
              <el-radio-button label="student">学生</el-radio-button>
              <el-radio-button label="teacher">教师</el-radio-button>
              <el-radio-button label="admin">管理员</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item prop="account">
            <el-input
              v-model="form.account"
              :placeholder="accountPlaceholder"
              :prefix-icon="User"
              class="custom-input"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              show-password
              :prefix-icon="Lock"
              @keyup.enter="handleLogin(formRef)"
              class="custom-input"
            />
          </el-form-item>

          <el-form-item>
            <el-button 
              type="primary" 
              class="submit-btn" 
              :loading="loading" 
              @click="handleLogin(formRef)"
            >
              立即登录 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
            </el-button>
          </el-form-item>
          
          <div class="form-footer">
            <span>忘记密码?</span>
            <span>演示账号: 20230001 / 123456</span>
          </div>
        </el-form>
      </div>

      <!-- 推拉门层 (顶层) -->
      <div class="sliding-doors">
        <div class="door left-door">
          <div class="door-content">
            <div class="tech-line"></div>
            <h2>AI 赋能</h2>
          </div>
        </div>
        <div class="door right-door">
          <div class="door-content">
            <div class="tech-line"></div>
            <h2>智能教务</h2>
          </div>
        </div>
        <!-- 初始文案 (居中) -->
        <div class="welcome-text">
          <div class="glow-text">欢迎来到 AI 赋能的教务系统</div>
          <div class="sub-glow">让你感受智能的教务体验</div>
          <div class="hover-hint">Hover to Login</div>
        </div>
      </div>
    </div>

    <!-- 右侧聊天面板：教�?-->
    <div class="side-panel right-panel">
      <div class="panel-header">
        <el-icon><Monitor /></el-icon>
        <span>教师 / TEACHER</span>
      </div>
      <div class="chat-content">
        <!-- 教师提问 -->
        <div class="chat-row teacher-row anim-fade-in">
          <div class="avatar-icon teacher-avatar">
            <el-icon><User /></el-icon>
          </div>
          <div class="bubble teacher-bubble">
            课件答疑怎么办？
          </div>
        </div>

        <!-- AI 回复 1 -->
        <div class="chat-row ai-row anim-slide-1">
          <div class="bubble ai-bubble">
            智能教案来帮你，备课答疑全搞�?
          </div>
          <div class="avatar-icon ai-avatar">
            <el-icon><Cpu /></el-icon>
          </div>
        </div>

        <!-- AI 回复 2 -->
        <div class="chat-row ai-row anim-slide-2">
          <div class="bubble ai-bubble">
            课件知识点自动匹配，答疑模板一键生�?
          </div>
          <div class="avatar-icon ai-avatar">
            <el-icon><Cpu /></el-icon>
          </div>
        </div>

        <!-- AI 回复 3 -->
        <div class="chat-row ai-row anim-slide-3 anim-scale">
          <div class="bubble ai-bubble">
            高效减负提质量，教学效率直接拉满
          </div>
          <div class="avatar-icon ai-avatar">
            <el-icon><Cpu /></el-icon>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 引入字体 */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Roboto+Mono:wght@400;500&display=swap');

/* 全局容器：深空背�?*/
.ai-login-container {
  height: 100vh;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #050505;
  position: relative;
  overflow: hidden;
  font-family: 'Inter', 'Microsoft YaHei', sans-serif; /* 确保中文显示正常 */
  gap: 60px;
}

/* 顶部系统标题�?*/
.top-bar {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 60px;
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
  background: linear-gradient(to bottom, rgba(0,0,0,0.8), transparent);
  border-bottom: 1px solid rgba(0, 242, 254, 0.1);
}

.top-bar-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.system-logo {
  display: flex;
  align-items: center;
  color: rgba(255, 255, 255, 0.9);
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 2px;
  text-shadow: 0 0 10px rgba(0, 242, 254, 0.5);
}

.logo-icon {
  margin-right: 10px;
  font-size: 24px;
  color: #00f2fe;
}

.system-en {
  font-family: 'Orbitron', sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 4px;
  margin-top: 2px;
}

/* 科技网格背景 */
.tech-grid {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: 
    linear-gradient(rgba(0, 242, 254, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 242, 254, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: 1;
}

/* 扫描线效�?*/
.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 5px;
  background: linear-gradient(to right, transparent, rgba(0, 242, 254, 0.5), transparent);
  animation: scan 8s linear infinite;
  z-index: 2;
  opacity: 0.3;
}

@keyframes scan {
  0% { top: -10%; }
  100% { top: 110%; }
}

/* 光晕装饰 */
.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  z-index: 0;
  opacity: 0.4;
}

.orb-1 {
  top: -100px;
  left: -100px;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, #409EFF, transparent);
  animation: floatOrb 10s ease-in-out infinite;
}

.orb-2 {
  bottom: -100px;
  right: -100px;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, #00f2fe, transparent);
  animation: floatOrb 12s ease-in-out infinite reverse;
}

@keyframes floatOrb {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, -30px); }
}

/* 侧边聊天面板 */
.side-panel {
  width: 320px;
  height: 500px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  z-index: 5;
}

.panel-header {
  display: flex;
  align-items: center;
  color: #00f2fe;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 20px;
  padding-left: 10px;
  border-left: 3px solid #00f2fe;
  background: linear-gradient(90deg, rgba(0, 242, 254, 0.1), transparent);
  padding: 8px 12px;
}

.panel-header .el-icon {
  margin-right: 8px;
  font-size: 18px;
}

.chat-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.chat-row {
  display: flex;
  align-items: flex-start;
  width: 100%;
  opacity: 0;
}

.student-row, .teacher-row {
  justify-content: flex-start;
}

.ai-row {
  justify-content: flex-end;
}

/* 头像图标 */
.avatar-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
}

.student-avatar, .teacher-avatar {
  margin-right: 12px;
}

.ai-avatar {
  margin-left: 12px;
  background: rgba(0, 242, 254, 0.1);
  border-color: #00f2fe;
  color: #00f2fe;
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.3);
}

/* 磨砂玻璃气泡 */
.bubble {
  max-width: 75%;
  padding: 14px 20px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  color: #fff;
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  position: relative;
  transition: all 0.3s ease;
}

.bubble:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(0, 242, 254, 0.3); /* Hover 时微�?*/
  box-shadow: 0 0 15px rgba(0, 242, 254, 0.1);
}

.student-bubble {
  border-left: 2px solid rgba(255, 255, 255, 0.3);
  border-top-left-radius: 0;
}

.teacher-bubble {
  border-left: 2px solid rgba(255, 255, 255, 0.3);
  border-top-left-radius: 0;
}

.ai-bubble {
  border-right: 2px solid #00f2fe;
  border-top-right-radius: 0;
  background: rgba(0, 242, 254, 0.05);
}

/* 核心交互盒子 */
.interaction-box {
  width: 800px;
  height: 500px;
  position: relative;
  border-radius: 4px;
  box-shadow: 0 0 50px rgba(0, 0, 0, 0.8);
  overflow: hidden;
  background: rgba(10, 10, 10, 0.6);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 242, 254, 0.2); /* 科技蓝边�?*/
  z-index: 10;
}

/* 边角装饰 */
.interaction-box::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 20px;
  height: 20px;
  border-top: 2px solid #00f2fe;
  border-left: 2px solid #00f2fe;
  z-index: 20;
}

.interaction-box::after {
  content: '';
  position: absolute;
  bottom: 0;
  right: 0;
  width: 20px;
  height: 20px;
  border-bottom: 2px solid #00f2fe;
  border-right: 2px solid #00f2fe;
  z-index: 20;
}

/* 登录表单�?*/
.login-form-layer {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px;
  box-sizing: border-box;
  background: transparent;
  color: #fff;
}

.form-header {
  text-align: center;
  margin-bottom: 40px;
}

.form-header h3 {
  font-size: 32px;
  margin: 0;
  background: linear-gradient(90deg, #fff, #00f2fe);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 2px;
  text-shadow: 0 0 20px rgba(0, 242, 254, 0.3);
}

.form-header p {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  margin-top: 10px;
  letter-spacing: 4px;
  text-transform: uppercase;
}

.login-form {
  width: 380px;
}

/* 覆盖 Element Plus 输入框样�?- 透明玻璃质感 */
:deep(.el-input__wrapper) {
  background-color: transparent !important;
  box-shadow: none !important;
  border: 1px solid rgba(0, 242, 254, 0.3);
  border-radius: 4px;
  padding: 5px 15px;
  transition: all 0.3s;
  backdrop-filter: blur(10px);
}

:deep(.el-input__wrapper:hover), :deep(.el-input__wrapper.is-focus) {
  background-color: rgba(0, 242, 254, 0.05) !important;
  border-color: #00f2fe !important;
  box-shadow: 0 0 15px rgba(0, 242, 254, 0.3) !important;
}

:deep(.el-input__inner) {
  color: #fff !important;
  height: 45px;
  font-family: 'Roboto Mono', monospace;
  letter-spacing: 1px;
  background: transparent !important;
}

:deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.4);
}

/* 角色选择器样�?*/
:deep(.el-radio-group) {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  padding: 4px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

:deep(.el-radio-button__inner) {
  background: transparent !important;
  border: none !important;
  color: rgba(255, 255, 255, 0.6) !important;
  border-radius: 2px !important;
  box-shadow: none !important;
  padding: 8px 20px;
  font-size: 14px;
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: rgba(0, 242, 254, 0.2) !important;
  color: #00f2fe !important;
  text-shadow: 0 0 5px rgba(0, 242, 254, 0.5);
}

.role-select {
  display: flex;
  justify-content: center;
  margin-bottom: 30px;
}

/* 按钮样式 */
.submit-btn {
  width: 100%;
  height: 50px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(90deg, rgba(0, 242, 254, 0.8), rgba(4, 93, 233, 0.8));
  border: none;
  border-radius: 4px;
  margin-top: 20px;
  transition: all 0.3s;
  letter-spacing: 2px;
  text-transform: uppercase;
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 0 20px rgba(0, 242, 254, 0.4);
  background: linear-gradient(90deg, #00f2fe, #409EFF);
}

.form-footer {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  margin-top: 25px;
  font-family: 'Roboto Mono', monospace;
}

/* 推拉门层 */
.sliding-doors {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  pointer-events: none; /* 让鼠标事件穿透到 interaction-box 来触�?hover */
  z-index: 10;
}

/* 恢复 Hover 交互 */
.interaction-box:hover .left-door {
  transform: translateX(-100%);
}

.interaction-box:hover .right-door {
  transform: translateX(100%);
}

.interaction-box:hover .welcome-text {
  opacity: 0;
  transform: scale(0.8);
  filter: blur(10px);
}

.door {
  flex: 1;
  height: 100%;
  background: rgba(5, 5, 5, 0.95);
  position: relative;
  transition: transform 0.8s cubic-bezier(0.65, 0, 0.35, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  overflow: hidden;
}

.left-door {
  border-right: 1px solid rgba(0, 242, 254, 0.2);
}

.right-door {
  border-left: 1px solid rgba(0, 242, 254, 0.2);
}

/* 门上的装饰内�?*/
.door-content {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  opacity: 0.4;
}

.left-door .door-content {
  right: 50px;
}

.right-door .door-content {
  left: 50px;
}

.tech-line {
  width: 1px;
  height: 120px;
  background: linear-gradient(to bottom, transparent, #00f2fe, transparent);
  margin-bottom: 20px;
  box-shadow: 0 0 10px #00f2fe;
}

.door h2 {
  font-size: 48px;
  color: rgba(255, 255, 255, 0.1);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 12px;
  writing-mode: vertical-rl;
  text-orientation: upright;
  text-shadow: 0 0 10px rgba(255, 255, 255, 0.1);
}

/* 欢迎文案 */
.welcome-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 20;
  transition: all 0.5s ease;
  width: 100%;
}

.glow-text {
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  text-shadow: 0 0 15px rgba(0, 242, 254, 0.8), 0 0 30px rgba(0, 242, 254, 0.4);
  margin-bottom: 15px;
  letter-spacing: 3px;
}

.sub-glow {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 6px;
  margin-bottom: 40px;
  text-transform: uppercase;
}

.hover-hint {
  font-family: 'Roboto Mono', monospace;
  font-size: 12px;
  color: #00f2fe;
  border: 1px solid rgba(0, 242, 254, 0.3);
  padding: 8px 24px;
  border-radius: 2px;
  display: inline-block;
  animation: pulse 2s infinite;
  background: rgba(0, 242, 254, 0.05);
}

@keyframes pulse {
  0% { opacity: 0.6; box-shadow: 0 0 0 rgba(0, 242, 254, 0); }
  50% { opacity: 1; box-shadow: 0 0 15px rgba(0, 242, 254, 0.3); }
  100% { opacity: 0.6; box-shadow: 0 0 0 rgba(0, 242, 254, 0); }
}

/* 动画定义 */
.anim-fade-in {
  animation: fadeIn 0.5s ease-out forwards;
}

.anim-slide-1 {
  animation: slideIn 0.5s ease-out forwards;
  animation-delay: 1.3s;
}

.anim-slide-2 {
  animation: slideIn 0.5s ease-out forwards;
  animation-delay: 2.2s;
}

.anim-slide-3 {
  animation: slideIn 0.5s ease-out forwards;
  animation-delay: 3.1s;
}

.anim-blink {
  animation: slideInAndBlink 4s ease-out forwards;
  animation-delay: 3.1s;
}

.anim-scale {
  animation: slideInAndScale 4s ease-out forwards;
  animation-delay: 3.1s;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes slideInAndBlink {
  0% { opacity: 0; transform: translateX(20px); }
  10% { opacity: 1; transform: translateX(0); }
  100% { opacity: 1; transform: translateX(0); }
  70% { opacity: 1; }
  75% { opacity: 0.5; }
  80% { opacity: 1; }
  85% { opacity: 0.5; }
  90% { opacity: 1; }
  95% { opacity: 0.5; }
}

@keyframes slideInAndScale {
  0% { opacity: 0; transform: translateX(20px) scale(1); }
  10% { opacity: 1; transform: translateX(0) scale(1); }
  80% { transform: scale(1); }
  90% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

/* 响应式适配 */
@media (max-width: 1400px) {
  .side-panel {
    display: none;
  }
  .ai-login-container {
    gap: 0;
  }
}
</style>




