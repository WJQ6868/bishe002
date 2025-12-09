<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'

const router = useRouter()
const theme = useTheme()
const drawer = ref(true)

const userRole = ref(localStorage.getItem('user_role') || 'student')
const userAccount = ref(localStorage.getItem('user_account') || '')

const menuItems = computed(() => {
  const role = userRole.value
  const allMenus = [
    { title: '仪表盘', icon: 'mdi-view-dashboard', to: '/material/dashboard', roles: ['admin', 'student', 'teacher'] },
    { title: '用户管理', icon: 'mdi-account-group', to: '/material/user-management', roles: ['admin'] },
    { title: '课程管理', icon: 'mdi-book-open-variant', to: '/material/course-management', roles: ['admin'] },
    { title: '排课管理', icon: 'mdi-calendar-multiselect', to: '/material/schedule', roles: ['admin'] },
    { title: '资源管理', icon: 'mdi-tools', to: '/material/resource-management', roles: ['admin'] },
    { title: '预约审核', icon: 'mdi-file-document-check', to: '/material/reservation-audit', roles: ['admin'] },
    { title: '系统配置', icon: 'mdi-cog', to: '/material/system-config', roles: ['admin'] },
    { title: '学情分析', icon: 'mdi-chart-box', to: '/material/analysis', roles: ['admin', 'teacher'] },
    { title: 'AI 智能助手', icon: 'mdi-robot', to: '/material/ai-qa', roles: ['student', 'teacher'] },
    { title: '即时通讯', icon: 'mdi-chat', to: '/material/instant-message', roles: ['student', 'teacher'] },
    { title: '选课中心', icon: 'mdi-mouse', to: '/material/student-course-select', roles: ['student'] },
    { title: '请假申请', icon: 'mdi-calendar-clock', to: '/material/student-leave', roles: ['student'] },
    { title: '我的作业', icon: 'mdi-book-edit-outline', to: '/material/student-homework', roles: ['student'] },
    { title: '成绩管理', icon: 'mdi-medal', to: '/material/student-grade-management', roles: ['student'] },
    { title: '智能教案', icon: 'mdi-file-document-edit-outline', to: '/material/teacher-lesson-plan', roles: ['teacher'] },
    { title: '成绩录入', icon: 'mdi-notebook-edit-outline', to: '/material/teacher-grade-management', roles: ['teacher'] },
    { title: '请假审批', icon: 'mdi-file-document-edit', to: '/material/teacher-leave-approval', roles: ['teacher'] },
    { title: '考勤管理', icon: 'mdi-account-check', to: '/material/teacher-attendance', roles: ['teacher'] },
    { title: '作业管理', icon: 'mdi-book-open-page-variant', to: '/material/teacher-homework', roles: ['teacher'] },
    { title: '工作安排', icon: 'mdi-calendar-clock', to: '/material/teacher-work-schedule', roles: ['teacher'] },
    { title: '校历安排', icon: 'mdi-calendar', to: '/material/calendar', roles: ['admin', 'teacher', 'student'] },
    { title: '办事大厅', icon: 'mdi-bank', to: '/material/service-hall', roles: ['admin', 'teacher', 'student'] },
    { title: '考试证书', icon: 'mdi-certificate', to: '/material/exam-certificates', roles: ['admin', 'teacher', 'student'] },
    { title: '返回经典版', icon: 'mdi-arrow-left', to: '/dashboard', roles: ['admin', 'student', 'teacher'] },
  ]
  return allMenus.filter(m => m.roles.includes(role))
})

const toggleTheme = () => {
  theme.global.name.value = theme.global.current.value.dark ? 'light' : 'dark'
}

const logout = () => {
  localStorage.removeItem('is_login')
  router.push('/login')
}
</script>

<template>
  <v-app>
    <v-navigation-drawer v-model="drawer" app>
      <v-list>
        <v-list-item
          prepend-avatar="https://randomuser.me/api/portraits/lego/1.jpg"
          :title="userAccount"
          :subtitle="userRole"
        ></v-list-item>
      </v-list>

      <v-divider></v-divider>

      <v-list density="compact" nav>
        <v-list-item
          v-for="item in menuItems"
          :key="item.title"
          :prepend-icon="item.icon"
          :title="item.title"
          :to="item.to"
          :value="item.title"
        ></v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-app-bar app color="primary" dark>
      <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
      <v-toolbar-title>智慧校园 (Material)</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn icon @click="toggleTheme">
        <v-icon>mdi-theme-light-dark</v-icon>
      </v-btn>
      <v-btn icon @click="logout">
        <v-icon>mdi-logout</v-icon>
      </v-btn>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <router-view></router-view>
      </v-container>
    </v-main>
  </v-app>
</template>
