<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { OfficeBuilding, Tickets, MagicStick } from '@element-plus/icons-vue'
import TeacherAIChat from '../components/TeacherAIChat.vue'
import StudentAIChat from '../components/StudentAIChat.vue'
import ThemeSwitcher from '../components/ThemeSwitcher.vue'
import { useThemeStore } from '../stores/theme'

const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()

const isDark = computed(() => themeStore.theme === 'dark')
const menuBg = computed(() => isDark.value ? '#141414' : '#304156')
const menuText = computed(() => isDark.value ? '#cfd3dc' : '#bfcbd9')
const logoBg = computed(() => isDark.value ? '#1f1f1f' : '#2b3649')

const userRole = ref(localStorage.getItem('user_role') || 'student')
const userAccount = ref(localStorage.getItem('user_account') || '')


const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗?', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
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
    { path: '/student/profile-center', title: '个人中心', icon: 'User', roles: ['student'] },
    { path: '/student/homework', title: '我的作业', icon: 'Edit', roles: ['student'] },
    { path: '/student/attendance', title: '上课签到', icon: 'Aim', roles: ['student'] },
    { path: '/teacher/lesson-plan', title: '智能教案', icon: 'Document', roles: ['teacher'] },
    { path: '/teacher/grade-management', title: '成绩管理', icon: 'DataLine', roles: ['teacher'] },
    { path: '/teacher/resource-reservation', title: '资源预约', icon: 'Timer', roles: ['teacher'] },
    { path: '/teacher/leave-approval', title: '请假审批', icon: 'Stamp', roles: ['teacher'] },
    { path: '/teacher/attendance', title: '上课点名', icon: 'Aim', roles: ['teacher'] },
    { path: '/teacher/homework', title: '作业管理', icon: 'EditPen', roles: ['teacher'] },
    { path: '/teacher/work-schedule', title: '工作安排', icon: 'Calendar', roles: ['teacher'] },
    { path: '/course', title: '课程管理', icon: 'Reading', roles: ['admin'] },
    { path: '/schedule', title: '排课管理', icon: 'Calendar', roles: ['admin'] },
    { path: '/user-management', title: '用户管理', icon: 'User', roles: ['admin'] },
    { path: '/admin/service-approval', title: '办事审批', icon: 'Stamp', roles: ['admin'] },
    { path: '/admin/class-adjust', title: '调课审批', icon: 'Stamp', roles: ['admin'] },
    { path: '/resource-management', title: '教学资源', icon: 'School', roles: ['admin'] },
    { path: '/reservation-audit', title: '预约审核', icon: 'Stamp', roles: ['admin'] },
    { path: '/ai-config', title: 'AI客服配置', icon: 'Service', roles: ['admin'] },
    { path: '/system-config', title: '系统配置', icon: 'Setting', roles: ['admin'] },
    { path: '/ai-qa', title: 'AI 智能助手', icon: 'ChatDotRound', roles: ['student', 'teacher'] },
    { path: '/academic/linkage', title: '专业班级联动', icon: 'Collection', roles: ['admin', 'teacher'] },
    { path: '/instant-message', title: '即时通讯', icon: 'ChatLineRound', roles: ['student', 'teacher'] },
    { path: '/analysis', title: '学情分析', icon: 'DataAnalysis', roles: ['admin', 'teacher'] },
    { path: '/material/dashboard', title: '切换至 Material 主题', icon: 'MagicStick', roles: ['admin', 'student', 'teacher'] },
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
    <el-aside width="220px">
      <el-menu
        :default-active="$route.path"
        class="el-menu-vertical"
        router
        :background-color="menuBg"
        :text-color="menuText"
        active-text-color="#409EFF"
      >
        <div class="logo" :style="{ backgroundColor: logoBg }">高校智能教务系统</div>
        
        <el-menu-item v-for="menu in menus" :key="menu.path" :index="menu.path">
          <el-icon>
            <component :is="menu.icon" />
          </el-icon>
          <span>{{ menu.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <div class="header-content">
          <h2>{{ route.meta.title }}</h2>
          <div class="user-info">
            <ThemeSwitcher />
            <span>{{ roleName }}: {{ userAccount }}</span>
            <el-button link type="primary" @click="handleLogout">退出</el-button>
          </div>
        </div>
      </el-header>
      <el-main>
        <router-view :key="$route.path" />
      </el-main>
    </el-container>
    
    <!-- 教师端 AI 客服组件 -->
    <TeacherAIChat v-if="userRole === 'teacher'" />
    <!-- 学生端 AI 客服组件 -->
    <StudentAIChat v-if="userRole === 'student'" />
  </el-container>
</template>

<style scoped>
.layout-container {
  height: 100vh;
}
.el-menu-vertical {
  height: 100%;
  border-right: none;
}
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: white;
  font-size: 18px;
  font-weight: bold;
  transition: background-color 0.3s;
}
.el-header {
  background-color: var(--header-bg-color);
  border-bottom: 1px solid var(--el-border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  transition: background-color 0.3s;
}
.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  color: var(--header-text-color);
}
.user-info {
  display: flex;
  gap: 15px;
  align-items: center;
  font-size: 14px;
  color: var(--header-text-color);
}
.el-main {
  background-color: var(--bg-color);
  padding: 20px;
  transition: background-color 0.3s;
}
</style>
