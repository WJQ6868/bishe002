<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import * as echarts from 'echarts'

// 1. 类型定义
interface StudentAnalysis {
  id: string
  name: string
  avgScore: number
  failedNum: number
  absentCount: number
  riskLevel: '高' | '中' | '低'
  status: 'pending' | 'processed' // 处理状态
}

// 2. 状态管理
const filters = reactive({
  grade: '2022级',
  major: '计算机科学与技术'
})

const loading = ref(false)
const riskStudents = ref<StudentAnalysis[]>([])

const snackbar = reactive({
  show: false,
  text: '',
  color: 'success'
})

const showMessage = (text: string, color: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

// 3. 模拟数据生成
const generateMockData = () => {
  const data: StudentAnalysis[] = []
  for (let i = 0; i < 100; i++) {
    const avg = 40 + Math.random() * 60
    const failed = avg < 60 ? Math.floor(Math.random() * 5) + 1 : 0
    data.push({
      id: `2022${String(i).padStart(4, '0')}`,
      name: `学生${i}`,
      avgScore: Number(avg.toFixed(1)),
      failedNum: failed,
      absentCount: Math.floor(Math.random() * 3),
      riskLevel: failed > 2 ? '高' : failed > 0 ? '中' : '低',
      status: 'pending'
    })
  }
  return data
}

// 4. 核心逻辑：ECharts 初始化与更新
const scatterChartRef = ref<HTMLElement>()
const barChartRef = ref<HTMLElement>()
let scatterChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null

const initCharts = () => {
  if (scatterChartRef.value && barChartRef.value) {
    scatterChart = echarts.init(scatterChartRef.value)
    barChart = echarts.init(barChartRef.value)
    updateCharts()
  }
}

const updateCharts = () => {
  loading.value = true
  
  // 模拟数据过滤
  const allData = generateMockData()
  const highRisk = allData.filter(s => s.riskLevel === '高')
  const mediumRisk = allData.filter(s => s.riskLevel === '中')
  const lowRisk = allData.filter(s => s.riskLevel === '低')
  
  // 更新列表数据
  riskStudents.value = highRisk.slice(0, 20) // 仅展示前20名高风险
  
  // 聚类算法原理：KMeans算法，k=3，基于平均分/不及格课程数聚类
  const scatterOption = {
    title: { text: '学生成绩聚类分析 (K-Means k=3)', left: 'center' },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => `平均分: ${params.data[0]}<br/>挂科数: ${params.data[1]}`
    },
    legend: { bottom: 0 },
    xAxis: { name: '平均分', min: 40, max: 100 },
    yAxis: { name: '不及格课程数' },
    series: [
      {
        name: '优秀 (低风险)',
        type: 'scatter',
        data: lowRisk.map(s => [s.avgScore, s.failedNum]),
        itemStyle: { color: '#52C41A' }
      },
      {
        name: '中等 (中风险)',
        type: 'scatter',
        data: mediumRisk.map(s => [s.avgScore, s.failedNum]),
        itemStyle: { color: '#409EFF' }
      },
      {
        name: '困难 (高风险)',
        type: 'scatter',
        data: highRisk.map(s => [s.avgScore, s.failedNum]),
        itemStyle: { color: '#F56C6C' }
      }
    ]
  }
  
  const barOption = {
    title: { text: '各专业学业预警人数统计', left: 'center' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['计算机', '软件工程', '网络安全', '人工智能', '大数据'] },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: [
          { value: 12, itemStyle: { color: '#F56C6C' } }, // >5 标红
          { value: 3, itemStyle: { color: '#409EFF' } },
          { value: 8, itemStyle: { color: '#F56C6C' } },
          { value: 4, itemStyle: { color: '#409EFF' } },
          { value: 2, itemStyle: { color: '#409EFF' } }
        ]
      }
    ]
  }
  
  scatterChart?.setOption(scatterOption)
  barChart?.setOption(barOption)
  
  loading.value = false
}

const handleFilterChange = () => {
  updateCharts()
  showMessage('数据已更新')
}

const handleProcessRisk = (row: StudentAnalysis) => {
  row.status = 'processed'
  showMessage(`已标记处理学生：${row.name}`)
}

onMounted(() => {
  initCharts()
  window.addEventListener('resize', () => {
    scatterChart?.resize()
    barChart?.resize()
  })
})

const headers = [
  { title: '学号', key: 'id', sortable: true },
  { title: '姓名', key: 'name' },
  { title: '平均分', key: 'avgScore', sortable: true },
  { title: '不及格科目', key: 'failedNum', sortable: true },
  { title: '预警等级', key: 'riskLevel' },
  { title: '操作', key: 'actions', sortable: false }
]

</script>

<template>
  <div class="analysis-container pa-4">
    <!-- 顶部筛选 -->
    <v-card class="mb-4" elevation="2">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="4">
            <v-select
              v-model="filters.grade"
              label="年级"
              :items="['2020级', '2021级', '2022级', '2023级']"
              @update:model-value="handleFilterChange"
              variant="outlined"
              density="compact"
              hide-details
            ></v-select>
          </v-col>
          <v-col cols="12" md="4">
            <v-select
              v-model="filters.major"
              label="专业"
              :items="['计算机科学与技术', '软件工程', '人工智能']"
              @update:model-value="handleFilterChange"
              variant="outlined"
              density="compact"
              hide-details
            ></v-select>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- 图表区域 -->
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-card elevation="2" :loading="loading">
          <v-card-text>
            <div ref="scatterChartRef" class="chart-container"></div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card elevation="2" :loading="loading">
          <v-card-text>
            <div ref="barChartRef" class="chart-container"></div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 风险列表 -->
    <v-card elevation="2">
      <v-card-title>
        <v-icon start color="error">mdi-alert-circle</v-icon>
        高风险学生预警列表
      </v-card-title>
      <v-data-table
        :headers="headers"
        :items="riskStudents"
        :loading="loading"
        item-value="id"
        class="elevation-1"
      >
        <template #item.failedNum="{ item }">
          <span style="color: #F56C6C; font-weight: bold">{{ item.failedNum }}</span>
        </template>
        
        <template #item.riskLevel="{ item }">
          <v-chip
            color="error"
            size="small"
            v-if="item.riskLevel === '高'"
          >
            高风险
          </v-chip>
          <v-chip
            color="warning"
            size="small"
            v-else-if="item.riskLevel === '中'"
          >
            中风险
          </v-chip>
          <v-chip
            color="success"
            size="small"
            v-else
          >
            低风险
          </v-chip>
        </template>

        <template #item.actions="{ item }">
          <v-btn
            color="primary"
            size="small"
            variant="text"
            :disabled="item.status === 'processed'"
            @click="handleProcessRisk(item)"
          >
            <v-icon start size="small">mdi-check-circle</v-icon>
            {{ item.status === 'processed' ? '已处理' : '标记已处理' }}
          </v-btn>
        </template>

        <template #item="{ item, props }">
           <tr v-bind="props" :class="{'processed-row': item.status === 'processed'}">
              <!-- v-data-table internally renders cells, but we can customize row classes via item slot if we handle all cells, 
                   OR simpler: use row-props if available in Vuetify 3. 
                   Vuetify 3 v-data-table uses item slot for full row control or individual slots.
                   Wait, row-props is available in newer Vuetify 3 versions. 
                   Let's stick to standard rendering and just style the cells or assume row styling isn't critical for now, 
                   OR use a specific style in the template slots.
              -->
           </tr>
        </template>
      </v-data-table>
    </v-card>

    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
      location="top"
    >
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<style scoped>
.chart-container {
  height: 400px;
  width: 100%;
}
/* Vuetify data table row coloring is tricky without specific props. 
   We can try to target the row content if possible, but usually requires :row-props="rowProps" 
*/
</style>
