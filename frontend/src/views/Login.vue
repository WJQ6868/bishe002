<script setup lang="ts">
import { reactive, ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import axios from 'axios'
import { User, Lock } from '@element-plus/icons-vue'

// 1. 类型定义
interface LoginForm {
  account: string
  password: string
  role: 'student' | 'teacher' | 'admin'
}

// 2. 状态定义
const formRef = ref<FormInstance>()
const loading = ref(false)
const router = useRouter()

const form = reactive<LoginForm>({
  account: '',
  password: '',
  role: 'student' // 默认学生
})

// 读取系统配置（演示：来自 SystemConfig 保存的 localStorage）
const systemName = ref('高校智能教务系统')
const loginBgKey = ref('')
const loginBgUrl = computed(() => {
  const map: Record<string, string> = {
    bg1: 'https://picsum.photos/1200/800?random=1',
    bg2: 'https://picsum.photos/1200/800?random=2',
    bg3: 'https://picsum.photos/1200/800?random=3'
  }
  return map[loginBgKey.value] || ''
})
onMounted(() => {
  try {
    const saved = localStorage.getItem('system_config')
    if (saved) {
      const parsed = JSON.parse(saved)
      systemName.value = parsed?.base?.systemName || systemName.value
      loginBgKey.value = parsed?.base?.loginBg || ''
    }
  } catch {}
})

// 3. 校验规则
const validateAccount = (rule: any, value: string, callback: any) => {
  if (value === '') {
    callback(new Error('请输入账号'))
  } else {
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
}

const rules = reactive<FormRules>({
  account: [{ validator: validateAccount, trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
})

// 4. 核心逻辑：模拟登录
const handleLogin = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  
  await formEl.validate(async (valid) => {
    if (valid) {
      loading.value = true
      
      try {
        const response = await axios.post('http://localhost:8000/token', {
          username: form.account,
          password: form.password,
          role: form.role  // 发送选择的角色
        })
        const { access_token } = response.data
        
        // Save token and fetch current user profile
        localStorage.setItem('token', access_token)
        axios.defaults.baseURL = 'http://localhost:8000'
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
    }
  })
}

const handleReset = (formEl: FormInstance | undefined) => {
  if (!formEl) return
  formEl.resetFields()
}

const getRoleName = (role: string) => {
  const map: Record<string, string> = {
    student: '同学',
    teacher: '老师',
    admin: '管理员'
  }
  return map[role] || ''
}

// 切换角色时重置校验
const handleRoleChange = () => {
  formRef.value?.clearValidate()
}
</script>

<template>
  <div class="login-container" :style="loginBgUrl ? { backgroundImage: `url(${loginBgUrl})`, backgroundSize: 'cover', backgroundPosition: 'center' } : {}">
    <div class="login-card">
      <div class="title-container">
        <h2>{{ systemName }}</h2>
        <p class="subtitle">Smart University Academic System</p>
      </div>
      
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="0"
        class="login-form"
        size="large"
      >
        <!-- 角色选择 -->
        <el-form-item prop="role" class="role-select">
          <el-radio-group v-model="form.role" @change="handleRoleChange">
            <el-radio label="student">学生</el-radio>
            <el-radio label="teacher">教师</el-radio>
            <el-radio label="admin">管理员</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 账号 -->
        <el-form-item prop="account">
          <el-input 
            v-model="form.account" 
            :placeholder="form.role === 'student' ? '请输入学号 (8位，2开头)' : form.role === 'teacher' ? '请输入工号 (6位，1开头)' : '请输入工号 (6位，8开头)'"
            :prefix-icon="User"
          />
        </el-form-item>

        <!-- 密码 -->
        <el-form-item prop="password">
          <el-input 
            v-model="form.password" 
            type="password" 
            placeholder="请输入密码" 
            show-password
            :prefix-icon="Lock"
            @keyup.enter="handleLogin(formRef)"
          />
        </el-form-item>

        <!-- 按钮组 -->
        <el-form-item>
          <div class="btn-group">
            <el-button 
              type="primary" 
              class="login-btn" 
              :loading="loading" 
              @click="handleLogin(formRef)"
              :color="form.role === 'teacher' ? '#52C41A' : form.role === 'admin' ? '#FAAD14' : '#409EFF'"
            >
              登录
            </el-button>
            <el-button class="reset-btn" @click="handleReset(formRef)">重置</el-button>
          </div>
        </el-form-item>
        
        <div class="demo-tips">
          <p>演示账号：学生(20230001) / 教师(100001) / 管理员(800001)</p>
          <p>统一密码：123456</p>
        </div>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  height: 100vh;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #E6F7FF 0%, #FFFFFF 100%);
}

.login-card {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}

.title-container {
  text-align: center;
  margin-bottom: 30px;
}

.title-container h2 {
  margin: 0;
  color: #303133;
  font-size: 24px;
  font-weight: 600;
}

.subtitle {
  margin: 10px 0 0;
  color: #909399;
  font-size: 14px;
}

.role-select {
  display: flex;
  justify-content: center;
  margin-bottom: 25px;
}

.btn-group {
  display: flex;
  width: 100%;
  gap: 16px;
}

.login-btn {
  flex: 2;
  font-weight: 600;
}

.reset-btn {
  flex: 1;
}

.demo-tips {
  margin-top: 20px;
  text-align: center;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  background: #f4f4f5;
  padding: 10px;
  border-radius: 4px;
}
</style>
