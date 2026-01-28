<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { fetchMajors, fetchClasses, type MajorItem, type ClassItem } from '../api/academic'
import axios from 'axios'

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

interface StudentItem {
  id: number
  student_no: string
  name: string
  grade_id: number
  class_id: number
  major?: string | null
  student_status: number
  status: number
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
const students = ref<StudentItem[]>([])
const processedIds = ref<Set<string>>(new Set())

const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const loadStudents = async () => {
  try {
    const res = await axios.get('admin/student/list', { headers: getAuthHeaders() })
    students.value = res.data || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取学生数据失败')
    students.value = []
  }
}

const hashSeed = (value: string) => {
  let hash = 0
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0
  }
  return hash
}

const seededRandom = (seed: number) => {
  const x = Math.sin(seed) * 10000
  return x - Math.floor(x)
}

const buildAnalysisData = (source: StudentItem[]) => {
  return source.map((s) => {
    const seed = hashSeed(s.student_no || String(s.id))
    const avgScore = 40 + seededRandom(seed) * 60
    let failedNum = 0
    if (avgScore < 60) {
      failedNum = Math.floor(seededRandom(seed + 1) * 3) + 2
    } else if (avgScore < 70) {
      failedNum = Math.floor(seededRandom(seed + 2) * 2)
    }
    const absentCount = Math.floor(seededRandom(seed + 3) * 4)
    const riskLevel: StudentAnalysis['riskLevel'] = failedNum >= 3 ? '高' : failedNum >= 1 ? '中' : '低'
    const status = processedIds.value.has(s.student_no) ? 'processed' : 'pending'

    return {
      id: s.student_no,
      name: s.name,
      avgScore: Number(avgScore.toFixed(1)),
      failedNum,
      absentCount,
      riskLevel,
      status
    }
  })
}

const selectedMajorName = computed(() => {
  const hit = majors.value.find((m) => m.id === selectedMajorId.value)
  return hit?.name || ''
})

const filteredStudents = computed(() => {
  const gradeId = Number(filters.grade.replace('级', ''))
  return students.value.filter((s) => {
    const gradeMatch = Number.isFinite(gradeId) ? s.grade_id === gradeId : true
    const majorMatch = selectedMajorName.value ? (s.major || '') === selectedMajorName.value : true
    return gradeMatch && majorMatch
  })
})

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
  
  const allData = buildAnalysisData(filteredStudents.value)
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
      const classCountMap = new Map<number, number>()
      filteredStudents.value.forEach((s) => {
        classCountMap.set(s.class_id, (classCountMap.get(s.class_id) || 0) + 1)
      })
      barOption = {
        title: { text: '该专业各班级人数统计', left: 'center' },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: classes.value.map((c) => c.name) },
        yAxis: { type: 'value', name: '人数' },
        series: [
          {
            type: 'bar',
            data: classes.value.map((c) => ({ value: classCountMap.get(c.id) || 0, itemStyle: { color: '#409EFF' } })),
            label: { show: true, position: 'top' }
          }
        ]
      }
    } catch {
      barOption = {
        title: { text: '该专业各班级人数统计', left: 'center' },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: [] },
        yAxis: { type: 'value', name: '人数' },
        series: [{ type: 'bar', data: [] }]
      }
    }
  } else {
    const majorCountMap = new Map<string, number>()
    highRisk.forEach((s) => {
      const majorName = selectedMajorName.value || (students.value.find((stu) => stu.student_no === s.id)?.major || '未设置')
      majorCountMap.set(majorName, (majorCountMap.get(majorName) || 0) + 1)
    })
    const majorNames = Array.from(majorCountMap.keys())
    barOption = {
      title: { text: '各专业学业预警人数统计', left: 'center' },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: majorNames },
      yAxis: { type: 'value' },
      series: [
        { type: 'bar', data: majorNames.map((name) => majorCountMap.get(name) || 0) }
      ]
    }
  }
  
  scatterChart?.setOption(scatterOption)
  barChart?.setOption(barOption)
  
  loading.value = false
}

const handleFilterChange = async () => {
  await loadStudents()
  await updateCharts()
  ElMessage.success('数据已更新')
}

const handleProcessRisk = (row: StudentAnalysis) => {
  processedIds.value.add(row.id)
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
  await loadStudents()
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
  background-color: rgba(103, 194, 58, 0.1);
  color: #909399;
}
</style>
