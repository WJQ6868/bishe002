<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { Reading, User, DataLine, School } from '@element-plus/icons-vue'

const stats = ref({
  total_courses: 0,
  total_students: 0,
  total_teachers: 0,
  available_classrooms: 0
})

const visitDates = ref<string[]>([])
const visitCounts = ref<number[]>([])

let timer: any = null
let chartInstance: any = null
let pieInstance: any = null

const fetchStats = async () => {
  try {
    const res = await axios.get('/dashboard/stats')
    stats.value = res.data
  } catch (e) {
    ElMessage.error('统计数据获取失败')
  }
}

const fetchVisits = async () => {
  try {
    const res = await axios.get('/dashboard/visits')
    const list = res.data || []
    visitDates.value = list.map((i: any) => i.date?.slice(5) || '')
    visitCounts.value = list.map((i: any) => Number(i.count || 0))
    updateCharts()
  } catch (e) {
    ElMessage.error('访问趋势获取失败')
  }
}

const buildPieData = () => {
  return [
    { value: Number(stats.value.total_courses || 0), name: '课程', itemStyle: { color: '#409EFF' } },
    { value: Number(stats.value.total_students || 0), name: '学生', itemStyle: { color: '#00f2fe' } },
    { value: Number(stats.value.total_teachers || 0), name: '教师', itemStyle: { color: '#67C23A' } },
    { value: Number(stats.value.available_classrooms || 0), name: '教室', itemStyle: { color: '#E6A23C' } }
  ]
}

const initCharts = () => {
  const chartDom = document.getElementById('activity-chart')
  const pieDom = document.getElementById('resource-chart')

  if (chartDom) {
    chartInstance = echarts.init(chartDom)
    chartInstance.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(20, 20, 20, 0.9)',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        textStyle: { color: '#fff' }
      },
      grid: { top: '15%', left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: [],
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.3)' } },
        axisLabel: { color: 'rgba(255,255,255,0.7)' }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
        axisLabel: { color: 'rgba(255,255,255,0.7)' }
      },
      series: [
        {
          name: '系统访问量',
          type: 'line',
          smooth: true,
          data: [],
          itemStyle: { color: '#00f2fe' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(0, 242, 254, 0.3)' },
              { offset: 1, color: 'rgba(0, 242, 254, 0.01)' }
            ])
          }
        }
      ]
    })
  }

  if (pieDom) {
    pieInstance = echarts.init(pieDom)
    pieInstance.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(20, 20, 20, 0.9)',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        textStyle: { color: '#fff' }
      },
      legend: {
        bottom: '5%',
        left: 'center',
        textStyle: { color: 'rgba(255,255,255,0.7)' }
      },
      series: [
        {
          name: '资源占比',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 10, borderColor: '#050505', borderWidth: 2 },
          label: { show: false, position: 'center' },
          emphasis: { label: { show: true, fontSize: 20, fontWeight: 'bold', color: '#fff' } },
          data: buildPieData()
        }
      ]
    })
  }
}

const updateCharts = () => {
  if (chartInstance) {
    chartInstance.setOption({
      xAxis: { data: visitDates.value.length ? visitDates.value : ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] },
      series: [{ name: '系统访问量', data: visitCounts.value.length ? visitCounts.value : [0, 0, 0, 0, 0, 0, 0] }]
    })
  }

  if (pieInstance) {
    pieInstance.setOption({
      series: [{ name: '资源占比', type: 'pie', data: buildPieData() }]
    })
  }
}

const handleRefresh = async () => {
  await Promise.all([fetchStats(), fetchVisits()])
  ElMessage.success('已刷新')
}

const resizeCharts = () => {
  chartInstance?.resize()
  pieInstance?.resize()
}

onMounted(async () => {
  initCharts()
  await Promise.all([fetchStats(), fetchVisits()])
  timer = setInterval(async () => {
    await Promise.all([fetchStats(), fetchVisits()])
  }, 60000)
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  window.removeEventListener('resize', resizeCharts)
  chartInstance?.dispose()
  pieInstance?.dispose()
})
</script>

<template>
  <div class="dashboard-container">
    <div class="welcome-banner">
      <div class="banner-content">
        <h2>欢迎回来，进入智能教务指挥中心</h2>
        <p>AI 赋能教育，数据驱动未来</p>
      </div>
      <el-button type="primary" class="refresh-btn" @click="handleRefresh">
        刷新数据
      </el-button>
    </div>

    <div class="stats-grid">
      <div class="tech-card stat-card">
        <div class="card-icon icon-blue">
          <el-icon><Reading /></el-icon>
        </div>
        <div class="card-info">
          <div class="stat-value">{{ stats.total_courses }}</div>
          <div class="stat-label">总课程数</div>
        </div>
        <div class="card-bg-glow"></div>
      </div>

      <div class="tech-card stat-card">
        <div class="card-icon icon-cyan">
          <el-icon><User /></el-icon>
        </div>
        <div class="card-info">
          <div class="stat-value">{{ stats.total_students }}</div>
          <div class="stat-label">在校学生</div>
        </div>
        <div class="card-bg-glow"></div>
      </div>

      <div class="tech-card stat-card">
        <div class="card-icon icon-green">
          <el-icon><DataLine /></el-icon>
        </div>
        <div class="card-info">
          <div class="stat-value">{{ stats.total_teachers }}</div>
          <div class="stat-label">专任教师</div>
        </div>
        <div class="card-bg-glow"></div>
      </div>

      <div class="tech-card stat-card">
        <div class="card-icon icon-orange">
          <el-icon><School /></el-icon>
        </div>
        <div class="card-info">
          <div class="stat-value">{{ stats.available_classrooms }}</div>
          <div class="stat-label">可用教室</div>
        </div>
        <div class="card-bg-glow"></div>
      </div>
    </div>

    <div class="charts-row">
      <div class="tech-card chart-card wide">
        <div class="card-header">
          <h3>系统访问趋势</h3>
        </div>
        <div id="activity-chart" class="chart-container"></div>
      </div>
      
      <div class="tech-card chart-card narrow">
        <div class="card-header">
          <h3>资源分布概览</h3>
        </div>
        <div id="resource-chart" class="chart-container"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 欢迎横幅 */
.welcome-banner {
  background: linear-gradient(90deg, rgba(0, 242, 254, 0.1), rgba(4, 93, 233, 0.1));
  border: 1px solid rgba(0, 242, 254, 0.2);
  border-radius: 8px;
  padding: 24px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  backdrop-filter: blur(10px);
}

.banner-content h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: #fff;
  letter-spacing: 1px;
}

.banner-content p {
  margin: 0;
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
}

.refresh-btn {
  background: rgba(0, 242, 254, 0.1);
  border: 1px solid #00f2fe;
  color: #00f2fe;
}

.refresh-btn:hover {
  background: #00f2fe;
  color: #000;
}

/* 统计卡片网格 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.tech-card {
  background: rgba(20, 20, 20, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 24px;
  position: relative;
  overflow: hidden;
  transition: transform 0.3s, box-shadow 0.3s;
}

.tech-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  border-color: rgba(0, 242, 254, 0.3);
}

.stat-card {
  display: flex;
  align-items: center;
}

.card-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  margin-right: 20px;
  background: rgba(255, 255, 255, 0.05);
}

.icon-blue { color: #409EFF; border: 1px solid rgba(64, 158, 255, 0.3); }
.icon-cyan { color: #00f2fe; border: 1px solid rgba(0, 242, 254, 0.3); }
.icon-green { color: #67C23A; border: 1px solid rgba(103, 194, 58, 0.3); }
.icon-orange { color: #E6A23C; border: 1px solid rgba(230, 162, 60, 0.3); }

.card-info { flex: 1; }
.stat-value { font-size: 28px; font-weight: 700; color: #fff; font-family: 'Orbitron', sans-serif; }
.stat-label { font-size: 14px; color: rgba(255, 255, 255, 0.5); margin-top: 4px; }

.card-bg-glow {
  position: absolute;
  top: -50%;
  right: -50%;
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(0, 242, 254, 0.1), transparent 70%);
  pointer-events: none;
}

/* 图表区域 */
.charts-row {
  display: flex;
  gap: 24px;
  height: 400px;
}

.chart-card { display: flex; flex-direction: column; }
.wide { flex: 2; }
.narrow { flex: 1; }

.card-header h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #fff;
  border-left: 4px solid #00f2fe;
  padding-left: 12px;
}

.chart-container { flex: 1; width: 100%; min-height: 0; }
</style>
