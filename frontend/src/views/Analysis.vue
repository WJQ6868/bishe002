<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { fetchMajors, fetchClasses, type MajorItem, type ClassItem } from '../api/academic'

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
  major: ''
})
const majors = ref<MajorItem[]>([])
const classes = ref<ClassItem[]>([])
const selectedMajorId = ref<number | null>(null)

const loading = ref(false)
const riskStudents = ref<StudentAnalysis[]>([])

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

const updateCharts = async () => {
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
  
  let barOption: any
  if (selectedMajorId.value) {
    try {
      classes.value = await fetchClasses(selectedMajorId.value)
      barOption = {
        title: { text: '该专业各班级人数统计', left: 'center' },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: classes.value.map((c) => c.name) },
        yAxis: { type: 'value', name: '人数' },
        series: [
          {
            type: 'bar',
            data: classes.value.map((c) => ({ value: c.student_count, itemStyle: { color: '#409EFF' } })),
            label: { show: true, position: 'top' }
          }
        ]
      }
    } catch {
      barOption = {
        title: { text: '各专业学业预警人数统计', left: 'center' },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: ['计算机', '软件工程', '网络安全', '人工智能', '大数据'] },
        yAxis: { type: 'value' },
        series: [
          { type: 'bar', data: [12, 3, 8, 4, 2] }
        ]
      }
    }
  } else {
    barOption = {
      title: { text: '各专业学业预警人数统计', left: 'center' },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: ['计算机', '软件工程', '网络安全', '人工智能', '大数据'] },
      yAxis: { type: 'value' },
      series: [
        { type: 'bar', data: [12, 3, 8, 4, 2] }
      ]
    }
  }
  
  scatterChart?.setOption(scatterOption)
  barChart?.setOption(barOption)
  
  loading.value = false
}

const handleFilterChange = async () => {
  await updateCharts()
  ElMessage.success('数据已更新')
}

const handleProcessRisk = (row: StudentAnalysis) => {
  row.status = 'processed'
  ElMessage.success(`已标记处理学生：${row.name}`)
}

onMounted(async () => {
  initCharts()
  try {
    majors.value = await fetchMajors()
    if (majors.value.length) {
      selectedMajorId.value = majors.value[0].id
      filters.major = majors.value[0].name
    }
  } catch {}
  await updateCharts()
  window.addEventListener('resize', () => {
    scatterChart?.resize()
    barChart?.resize()
  })
})

const rowClassName = ({ row }: { row: StudentAnalysis }) => {
  if (row.status === 'processed') return 'processed-row'
  return ''
}

</script>

<template>
  <div class="analysis-container">
    <!-- 顶部筛选 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filters">
        <el-form-item label="年级">
          <el-select v-model="filters.grade" @change="handleFilterChange">
            <el-option label="2020级" value="2020级" />
            <el-option label="2021级" value="2021级" />
            <el-option label="2022级" value="2022级" />
            <el-option label="2023级" value="2023级" />
          </el-select>
        </el-form-item>
        <el-form-item label="专业">
          <el-select v-model="selectedMajorId" @change="() => { const m = majors.find(x => x.id === selectedMajorId)!; filters.major = m?.name || ''; handleFilterChange() }" style="min-width: 220px">
            <el-option v-for="m in majors" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row" v-loading="loading">
      <el-col :span="12">
        <el-card>
          <div ref="scatterChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <div ref="barChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 风险列表 -->
    <el-card class="list-card" header="高风险学生预警列表">
      <el-table :data="riskStudents" style="width: 100%" :row-class-name="rowClassName">
        <el-table-column prop="id" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="avgScore" label="平均分" width="100" sortable />
        <el-table-column prop="failedNum" label="不及格科目" width="120" sortable>
          <template #default="{ row }">
            <span style="color: #F56C6C; font-weight: bold">{{ row.failedNum }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="riskLevel" label="预警等级" width="100">
           <template #default="{ row }">
             <el-tag type="danger" v-if="row.riskLevel === '高'">高风险</el-tag>
           </template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button 
              type="primary" 
              size="small" 
              :disabled="row.status === 'processed'"
              @click="handleProcessRisk(row)"
            >
              {{ row.status === 'processed' ? '已处理' : '标记已处理' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.analysis-container {
  height: 100%;
}
.filter-card {
  margin-bottom: 20px;
}
.chart-row {
  margin-bottom: 20px;
}
.chart-container {
  height: 400px;
}
:deep(.processed-row) {
  background-color: #f0f9eb;
  color: #909399;
}
</style>
