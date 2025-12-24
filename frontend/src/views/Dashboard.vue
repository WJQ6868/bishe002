<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const stats = ref({
  total_courses: 0,
  total_students: 0,
  total_teachers: 0,
  available_classrooms: 0
})

let timer: any = null

const fetchStats = async () => {
  try {
    const res = await axios.get('/dashboard/stats')
    stats.value = res.data
  } catch (e) {
    ElMessage.error('统计数据获取失败')
  }
}

const handleRefresh = async () => {
  await fetchStats()
  ElMessage.success('已刷新')
}

onMounted(async () => {
  await fetchStats()
  timer = setInterval(fetchStats, 60000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="dashboard">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>欢迎使用高校智能教务系统</span>
          <div style="float:right">
            <el-button size="small" type="primary" @click="handleRefresh">刷新</el-button>
          </div>
        </div>
      </template>
      <div class="content">
        <p>本系统集成了智能排课、学情分析与 AI 助教服务，致力于提升教育管理效率。</p>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-statistic title="总课程数" :value="stats.total_courses" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="在校学生" :value="stats.total_students" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="专任教师" :value="stats.total_teachers" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="可用教室" :value="stats.available_classrooms" />
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 20px;
}
.content {
  padding: 20px 0;
}
</style>
