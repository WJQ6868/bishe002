<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const stats = ref({
  total_courses: 0,
  total_students: 0,
  total_teachers: 0,
  available_classrooms: 0
})

const loading = ref(false)
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('error')

const fetchStats = async () => {
  loading.value = true
  try {
    const res = await axios.get('/dashboard/stats', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    stats.value = res.data
  } catch (e) {
    snackbarText.value = '统计数据获取失败'
    snackbarColor.value = 'error'
    snackbar.value = true
  } finally {
    loading.value = false
  }
}

onMounted(fetchStats)
</script>

<template>
  <v-container fluid>
    <v-card class="mb-6" elevation="2">
      <v-card-title class="text-h6">欢迎使用高校智能教务系统</v-card-title>
      <v-card-text>
        本系统集成了智能排课、学情分析与 AI 助教服务，致力于提升教育管理效率。
      </v-card-text>
    </v-card>

    <v-row>
      <v-col cols="12" sm="6" md="3">
        <v-card class="pa-4 text-center" elevation="1">
          <div class="text-caption text-grey">总课程数</div>
          <div class="text-h5 font-weight-bold">{{ stats.total_courses }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card class="pa-4 text-center" elevation="1">
          <div class="text-caption text-grey">在校学生</div>
          <div class="text-h5 font-weight-bold">{{ stats.total_students.toLocaleString() }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card class="pa-4 text-center" elevation="1">
          <div class="text-caption text-grey">专任教师</div>
          <div class="text-h5 font-weight-bold">{{ stats.total_teachers }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card class="pa-4 text-center" elevation="1">
          <div class="text-caption text-grey">可用教室</div>
          <div class="text-h5 font-weight-bold">{{ stats.available_classrooms }}</div>
        </v-card>
      </v-col>
    </v-row>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mt-4"></v-progress-linear>

    <v-snackbar v-model="snackbar" :color="snackbarColor" timeout="3000" location="top">
      {{ snackbarText }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<style scoped>
.pa-4 { padding: 16px; }
</style>
