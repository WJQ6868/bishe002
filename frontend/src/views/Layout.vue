<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { computed, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import TeacherAIChat from '../components/TeacherAIChat.vue'
import StudentAIChat from '../components/StudentAIChat.vue'
import { useThemeStore } from '../stores/theme'
import { Cpu, SwitchButton, UserFilled } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()

// 强制深色模式逻辑 (配合 CSS)
const isDark = computed(() => true) 

const userRole = ref(localStorage.getItem('user_role') || 'student')
const userAccount = ref(localStorage.getItem('user_account') || '')
const systemName = ref('高校智能教务系统')

onMounted(() => {
  try {
    const saved = localStorage.getItem('system_config')
    if (saved) {
      const parsed = JSON.parse(saved)
      systemName.value = parsed?.base?.systemName || systemName.value
    }
  } catch {}
})

const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗?', '系统提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
    customClass: 'tech-message-box'
  }).then(() => {
    localStorage.removeItem('is_login')
    localStorage.removeItem('user_role')
    localStorage.removeItem('user_account')
    router.push('/login')
    ElMessage.success('已退出登录')
  })
}

// 根据角色显示菜单
const menus = computed(() => {
  const role = userRole.value
  const allMenus = [
    { path: '/dashboard', title: '系统首页', icon: 'Odometer', roles: ['admin', 'student', 'teacher'] },
    { path: '/service/hall', title: '办事大厅', icon: 'OfficeBuilding', roles: ['admin', 'student', 'teacher'] },
    { path: '/cert/links', title: '考试证书', icon: 'Link', roles: ['admin', 'student', 'teacher'] },
    { path: '/student/course-select', title: '选课中心', icon: 'Mouse', roles: ['student'] },
    { path: '/student/course-management', title: '选课管理', icon: 'List', roles: ['student'] },
    { path: '/student/grade-management', title: '成绩管理', icon: 'Medal', roles: ['student'] },
    { path: '/student/ai-course-assistant', title: 'AI课程助手', icon: 'Search', roles: ['student'] },
    { path: '/student/profile-center', title: '个人中心', icon: 'User', roles: ['student'] },
    { path: '/student/homework', title: '我的作业', icon: 'Edit', roles: ['student'] },

    { path: '/teacher/lesson-plan', title: '智能教案', icon: 'Document', roles: ['teacher'] },
    { path: '/teacher/course-assistant', title: 'AI课程助手', icon: 'Search', roles: ['teacher'] },
    { path: '/teacher/grade-management', title: '成绩管理', icon: 'DataLine', roles: ['teacher'] },
    { path: '/teacher/resource-reservation', title: '资源预约', icon: 'Timer', roles: ['teacher'] },
    { path: '/teacher/leave-approval', title: '请假审批', icon: 'Stamp', roles: ['teacher'] },

    { path: '/teacher/homework', title: '作业管理', icon: 'EditPen', roles: ['teacher'] },
    { path: '/teacher/work-schedule', title: '工作安排', icon: 'Calendar', roles: ['teacher'] },
    { path: '/course', title: '课程管理', icon: 'Reading', roles: ['admin'] },
    { path: '/schedule', title: '排课管理', icon: 'Calendar', roles: ['admin'] },
    { path: '/academic/college-major', title: '学院专业管理', icon: 'School', roles: ['admin'] },
    { path: '/academic/linkage', title: '专业班级管理', icon: 'Collection', roles: ['admin'] },
    { path: '/admin/teacher-users', title: '教职工用户管理', icon: 'User', roles: ['admin'] },
    { path: '/admin/student-users', title: '学生用户管理', icon: 'User', roles: ['admin'] },
    { path: '/admin/class-adjust', title: '调课审批', icon: 'Stamp', roles: ['admin'] },
    { path: '/resource-management', title: '教学资源', icon: 'School', roles: ['admin'] },
    { path: '/reservation-audit', title: '预约审核', icon: 'Stamp', roles: ['admin'] },
    { path: '/ai-config', title: 'AI设置', icon: 'Service', roles: ['admin'] },
    { path: '/system-config', title: '系统配置', icon: 'Setting', roles: ['admin'] },
    { path: '/instant-message', title: '即时通讯', icon: 'ChatLineRound', roles: ['student', 'teacher'] },
    { path: '/analysis', title: '学情分析', icon: 'DataAnalysis', roles: ['admin', 'teacher'] },
  ]
  
  return allMenus.filter(m => m.roles.includes(role))
})

const roleName = computed(() => {
  const map: Record<string, string> = {
    student: '学生',
    teacher: '教师',
    admin: '管理员'
  }
  return map[userRole.value] || userRole.value
})
</script>

<template>
  <el-container class="layout-container">
    <!-- 背景装饰 -->
    <div class="tech-grid"></div>
    <div class="scan-line"></div>
    
    <el-aside width="240px" class="tech-aside">
      <div class="logo-container">
        <el-icon class="logo-icon"><Cpu /></el-icon>
        <span class="logo-text">{{ systemName }}</span>
      </div>
      
      <el-menu
        :default-active="$route.path"
        class="tech-menu"
        router
        :unique-opened="true"
      >
        <el-menu-item v-for="menu in menus" :key="menu.path" :index="menu.path">
          <el-icon>
            <component :is="menu.icon" />
          </el-icon>
          <span>{{ menu.title }}</span>
          <div class="active-bar"></div>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container class="main-container">
      <el-header class="tech-header">
        <div class="header-left">
          <h2 class="page-title">{{ route.meta.title }}</h2>
          <div class="breadcrumb-line"></div>
        </div>
        
        <div class="header-right">
          <div class="user-profile">
            <el-avatar :size="32" :icon="UserFilled" class="user-avatar" />
            <div class="user-info">
              <span class="user-name">{{ userAccount }}</span>
              <span class="user-role">{{ roleName }}</span>
            </div>
          </div>
          <el-divider direction="vertical" class="header-divider" />
          <div class="logout-btn" @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            <span>退出</span>
          </div>
        </div>
      </el-header>
      
      <el-main class="tech-main">
        <router-view v-slot="{ Component }">
          <transition name="fade-transform" mode="out-in">
            <component :is="Component" :key="$route.path" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
    
    <!-- 教师端 AI 客服组件 -->
    <TeacherAIChat v-if="userRole === 'teacher'" />
    <!-- 学生端 AI 客服组件 -->
    <StudentAIChat v-if="userRole === 'student'" />
    
  </el-container>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');

.layout-container {
  height: 100vh;
  background: #050505;
  color: #fff;
  position: relative;
  overflow: hidden;
}

/* 背景特效 */
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
  z-index: 0;
}

.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(to right, transparent, rgba(0, 242, 254, 0.3), transparent);
  animation: scan 10s linear infinite;
  z-index: 1;
  pointer-events: none;
}

@keyframes scan {
  0% { top: -10%; }
  100% { top: 110%; }
}

/* 侧边栏样式 */
.tech-aside {
  background: rgba(10, 10, 10, 0.6);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(0, 242, 254, 0.1);
  z-index: 10;
  display: flex;
  flex-direction: column;
}

.logo-container {
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(0, 242, 254, 0.1);
  background: linear-gradient(to right, rgba(0, 242, 254, 0.05), transparent);
}

.logo-icon {
  font-size: 24px;
  color: #00f2fe;
  margin-right: 10px;
  filter: drop-shadow(0 0 5px rgba(0, 242, 254, 0.5));
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 1px;
}

.tech-menu {
  background: transparent !important;
  border-right: none;
  padding-top: 20px;
}

:deep(.el-menu-item) {
  background: transparent !important;
  color: rgba(255, 255, 255, 0.6) !important;
  height: 56px;
  margin: 4px 12px;
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}

:deep(.el-menu-item:hover) {
  background: rgba(0, 242, 254, 0.05) !important;
  color: #fff !important;
}

:deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(0, 242, 254, 0.15), rgba(0, 242, 254, 0.05)) !important;
  color: #00f2fe !important;
  font-weight: 600;
}

.active-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #00f2fe;
  opacity: 0;
  transition: opacity 0.3s;
  box-shadow: 0 0 10px #00f2fe;
}

:deep(.el-menu-item.is-active) .active-bar {
  opacity: 1;
}

/* 头部样式 */
.tech-header {
  height: 80px;
  background: rgba(10, 10, 10, 0.4);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0, 242, 254, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 30px;
  z-index: 10;
}

.header-left {
  display: flex;
  flex-direction: column;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  margin: 0;
  letter-spacing: 1px;
}

.breadcrumb-line {
  width: 40px;
  height: 2px;
  background: #00f2fe;
  margin-top: 5px;
  box-shadow: 0 0 5px rgba(0, 242, 254, 0.5);
}

.header-right {
  display: flex;
  align-items: center;
}

.user-profile {
  display: flex;
  align-items: center;
  margin-right: 20px;
}

.user-avatar {
  background: rgba(0, 242, 254, 0.1);
  color: #00f2fe;
  border: 1px solid rgba(0, 242, 254, 0.3);
}

.user-info {
  display: flex;
  flex-direction: column;
  margin-left: 10px;
}

.user-name {
  font-size: 14px;
  color: #fff;
}

.user-role {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.header-divider {
  border-color: rgba(255, 255, 255, 0.1);
  height: 20px;
  margin: 0 20px;
}

.logout-btn {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.6);
  transition: color 0.3s;
}

.logout-btn:hover {
  color: #ff4d4f;
}

.logout-btn .el-icon {
  margin-right: 5px;
}

/* 主内容区 */
.tech-main {
  padding: 20px;
  overflow-y: auto;
  position: relative;
  z-index: 5;
}

/* 路由过渡动画 */
.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>

<style>
/* 全局覆盖 Element Plus 样式以适应深色科技风 */
.tech-message-box {
  background: rgba(10, 10, 10, 0.9) !important;
  border: 1px solid rgba(0, 242, 254, 0.3) !important;
  backdrop-filter: blur(10px);
}

.tech-message-box .el-message-box__title {
  color: #fff !important;
}

.tech-message-box .el-message-box__message {
  color: rgba(255, 255, 255, 0.8) !important;
}

.tech-message-box .el-button--primary {
  background: #00f2fe !important;
  border-color: #00f2fe !important;
  color: #000 !important;
}
</style>
