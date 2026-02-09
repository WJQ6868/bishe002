<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Download, Check, Edit } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import axios from 'axios'

// --- 1. 类型定义 ---
/**
 * 学生成绩记录
 */
interface StudentScore {
  id: string
  studentId: string
  name: string
  className: string
  usualScore: number | null      // 平均成绩（期中+期末）
  midtermScore: number | null    // 期中成绩
  finalScore: number | null      // 期末成绩
  totalScore: number | null      // 总评成绩
  gpa: number | null             // 绩点
}

/**
 * 成绩统计
 */
interface ScoreStat {
  average: number
  highest: number
  lowest: number
  passRate: number
  excellentRate: number
}

interface CourseOption {
  id: number
  name: string
  course_type?: string | null
}

// --- 3. 状态管理 ---
const courses = ref<CourseOption[]>([])
const selectedCourse = ref<number | null>(null)
const studentScores = ref<StudentScore[]>([])
const loading = ref(false)
const listLoading = ref(false)
const hasUnsavedChanges = ref(false)
const editDialogVisible = ref(false)
const currentStudent = ref<StudentScore | null>(null)

// ECharts图表
const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

// --- 4. 核心逻辑 ---

/**
 * 计算总评成绩
 * 公式：总评 = 平均30% + 期中30% + 期末40%
 */
const calculateTotalScore = (student: StudentScore) => {
  if (student.midtermScore !== null && student.finalScore !== null) {
    student.usualScore = Math.round((student.midtermScore + student.finalScore) / 2)
  } else {
    student.usualScore = null
  }
  if (student.usualScore !== null && student.midtermScore !== null && student.finalScore !== null) {
    student.totalScore = Math.round(
      student.usualScore * 0.3 + student.midtermScore * 0.3 + student.finalScore * 0.4
    )
    // 计算绩点（绩点 = 分数/10 - 5，60分以下为0）
    student.gpa = student.totalScore < 60 ? 0 : Number(((student.totalScore / 10) - 5).toFixed(1))
  } else {
    student.totalScore = null
    student.gpa = null
  }
}

// 成绩统计
const statistics = computed<ScoreStat>(() => {
  const validScores = studentScores.value.filter(s => s.totalScore !== null)
  if (validScores.length === 0) {
    return { average: 0, highest: 0, lowest: 0, passRate: 0, excellentRate: 0 }
  }
  
  const scores = validScores.map(s => s.totalScore!)
  const average = scores.reduce((sum, s) => sum + s, 0) / scores.length
  const highest = Math.max(...scores)
  const lowest = Math.min(...scores)
  const passCount = scores.filter(s => s >= 60).length
  const excellentCount = scores.filter(s => s >= 90).length
  
  return {
    average: Number(average.toFixed(1)),
    highest,
    lowest,
    passRate: Number((passCount / validScores.length * 100).toFixed(1)),
    excellentRate: Number((excellentCount / validScores.length * 100).toFixed(1))
  }
})

// 成绩分布数据
const scoreDistribution = computed(() => {
  const validScores = studentScores.value.filter(s => s.totalScore !== null)
  const distribution = {
    '0-59': 0,
    '60-69': 0,
    '70-79': 0,
    '80-89': 0,
    '90-100': 0
  }
  
  validScores.forEach(s => {
    const score = s.totalScore!
    if (score < 60) distribution['0-59']++
    else if (score < 70) distribution['60-69']++
    else if (score < 80) distribution['70-79']++
    else if (score < 90) distribution['80-89']++
    else distribution['90-100']++
  })
  
  return distribution
})

// 单元格编辑
const handleCellEdit = (row: StudentScore, field: 'midtermScore' | 'finalScore', value: number | null) => {
  row[field] = value
  calculateTotalScore(row)
  hasUnsavedChanges.value = true
}

// 打开编辑弹窗
const openEditDialog = (student: StudentScore) => {
  currentStudent.value = { ...student }
  if (currentStudent.value) {
    calculateTotalScore(currentStudent.value)
  }
  editDialogVisible.value = true
}

// 保存单个学生成绩
const saveStudentScore = async () => {
  if (!currentStudent.value) return
  if (!selectedCourse.value) {
    ElMessage.warning('请先选择课程')
    return
  }
  
  try {
    loading.value = true
    await axios.post('/teacher/grades/save', {
      course_id: selectedCourse.value,
      items: [{
        student_id: currentStudent.value.studentId,
        midterm_score: currentStudent.value.midtermScore,
        final_score: currentStudent.value.finalScore
      }]
    })
    const index = studentScores.value.findIndex(s => s.id === currentStudent.value!.id)
    if (index !== -1) {
      calculateTotalScore(currentStudent.value)
      studentScores.value[index] = { ...currentStudent.value }
    }
    hasUnsavedChanges.value = false
    editDialogVisible.value = false
    ElMessage.success('成绩修改成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '成绩保存失败')
  } finally {
    loading.value = false
  }
}

// 批量导入
const handleImport = async () => {
  if (!selectedCourse.value) {
    ElMessage.warning('请先选择课程')
    return
  }
  // 模拟填充所有学生成绩
  studentScores.value.forEach(student => {
    if (student.midtermScore === null && student.finalScore === null) {
      student.midtermScore = Math.floor(Math.random() * 20 + 70)
      student.finalScore = Math.floor(Math.random() * 20 + 70)
      calculateTotalScore(student)
    }
  })
  hasUnsavedChanges.value = true
  updateChart()
  await saveAllScores()
}

// 批量导出
const handleExport = () => {
  ElMessage.success('正在导出成绩表...（模拟）')
  setTimeout(() => {
    ElMessage.success('成绩表导出成功！')
  }, 1000)
}

// 保存成绩
const saveAllScores = async () => {
  if (!selectedCourse.value) {
    ElMessage.warning('请先选择课程')
    return
  }
  loading.value = true
  try {
    const items = studentScores.value
      .filter((s) => s.midtermScore !== null || s.finalScore !== null)
      .map((s) => ({
        student_id: s.studentId,
        midterm_score: s.midtermScore,
        final_score: s.finalScore
      }))
    await axios.post('/teacher/grades/save', {
      course_id: selectedCourse.value,
      items
    })
    hasUnsavedChanges.value = false
    ElMessage.success('成绩保存成功')
    await loadStudents()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '成绩保存失败')
  } finally {
    loading.value = false
  }
}

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

// 更新图表
const updateChart = () => {
  if (!chartInstance) return
  
  const dist = scoreDistribution.value
  const option = {
    backgroundColor: 'transparent',
    title: {
      text: '成绩分布统计',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
        color: '#fff'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      backgroundColor: 'rgba(20, 20, 20, 0.9)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: { color: '#fff' }
    },
    grid: { top: 50, left: '6%', right: '4%', bottom: 30, containLabel: true },
    xAxis: {
      type: 'category',
      data: ['0-59分', '60-69分', '70-79分', '80-89分', '90-100分'],
      axisLabel: {
        rotate: 0,
        color: 'rgba(255,255,255,0.7)'
      },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } }
    },
    yAxis: {
      type: 'value',
      name: '人数',
      minInterval: 1,
      axisLabel: { color: 'rgba(255,255,255,0.7)' },
      nameTextStyle: { color: 'rgba(255,255,255,0.7)' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } }
    },
    series: [{
      name: '人数',
      type: 'bar',
      data: Object.values(dist),
      barWidth: 26,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(0, 242, 254, 0.85)' },
          { offset: 1, color: 'rgba(0, 242, 254, 0.2)' }
        ])
      },
      label: {
        show: true,
        position: 'top',
        color: '#fff'
      }
    }]
  }
  
  chartInstance.setOption(option)
}

const loadCourses = async () => {
  try {
    const res = await axios.get('/teacher/grades/courses')
    courses.value = Array.isArray(res.data?.items) ? res.data.items : res.data || []
    if (courses.value.length && !selectedCourse.value) {
      selectedCourse.value = courses.value[0].id
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '课程加载失败')
    courses.value = []
  }
}

const loadStudents = async () => {
  if (!selectedCourse.value) {
    studentScores.value = []
    return
  }
  listLoading.value = true
  try {
    const res = await axios.get('/teacher/grades/students', { params: { course_id: selectedCourse.value } })
    const items = Array.isArray(res.data?.items) ? res.data.items : []
    studentScores.value = items.map((item: any) => {
      const row: StudentScore = {
        id: String(item.student_id),
        studentId: String(item.student_id),
        name: item.name || '',
        className: item.class_name || '—',
        usualScore: null,
        midtermScore: item.midterm_score ?? null,
        finalScore: item.final_score ?? null,
        totalScore: null,
        gpa: null
      }
      calculateTotalScore(row)
      return row
    })
    hasUnsavedChanges.value = false
    nextTick(() => updateChart())
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '学生成绩加载失败')
    studentScores.value = []
  } finally {
    listLoading.value = false
  }
}

onMounted(async () => {
  initChart()
  await loadCourses()
  await loadStudents()
})

watch(selectedCourse, async () => {
  await loadStudents()
})

watch(
  () => [currentStudent.value?.midtermScore, currentStudent.value?.finalScore],
  () => {
    if (currentStudent.value) {
      calculateTotalScore(currentStudent.value)
    }
  }
)

// 监听成绩变化，动态刷新图表
watch(studentScores, () => {
  nextTick(() => updateChart())
}, { deep: true })
</script>

<template>
  <div class="teacher-grade-container">
    <!-- 顶部操作栏 -->
    <el-card class="header-card">
      <div class="header-bar">
        <div class="left-section">
          <span style="margin-right: 10px">选择课程：</span>
          <el-select v-model="selectedCourse" style="width: 220px" :disabled="courses.length === 0">
            <el-option
              v-for="course in courses"
              :key="course.id"
              :label="course.course_type ? `${course.name} (${course.course_type})` : course.name"
              :value="course.id"
            />
          </el-select>
        </div>
        <div class="right-section">
          <el-button :icon="Upload" :disabled="!selectedCourse" @click="handleImport">批量导入</el-button>
          <el-button :icon="Download" :disabled="studentScores.length === 0" @click="handleExport">批量导出</el-button>
          <el-button 
            type="success" 
            :icon="Check" 
            :disabled="!hasUnsavedChanges"
            :loading="loading"
            @click="saveAllScores"
          >
            保存成绩
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 成绩统计 -->
    <div class="statistics-section">
      <el-row :gutter="20">
        <el-col :span="4">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-label">平均分</div>
              <div class="stat-value">{{ statistics.average }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="4">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-label">最高分</div>
              <div class="stat-value success">{{ statistics.highest }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="4">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-label">最低分</div>
              <div class="stat-value danger">{{ statistics.lowest }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-label">及格率</div>
              <div class="stat-value primary">{{ statistics.passRate }}%</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-label">优秀率</div>
              <div class="stat-value warning">{{ statistics.excellentRate }}%</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 成绩分布图 -->
    <el-card class="chart-card">
      <div ref="chartRef" class="chart-container"></div>
    </el-card>

    <!-- 成绩列表 -->
    <el-card class="table-card">
      <template #header>
        <span>学生成绩列表（{{ studentScores.length }}人）</span>
      </template>
      <el-table
        v-loading="listLoading"
        :data="studentScores"
        style="width: 100%"
        border
        height="520"
      >
        <el-table-column prop="studentId" label="学号" width="120" fixed />
        <el-table-column prop="name" label="姓名" width="100" fixed />
        <el-table-column prop="className" label="班级" width="120" />
        <el-table-column label="平均成绩" width="120" align="center">
          <template #default="{ row }">
            <span class="avg-score">{{ row.usualScore ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="期中成绩" width="120" align="center">
          <template #default="{ row }">
            <el-input-number
              v-model="row.midtermScore"
              :min="0"
              :max="100"
              :precision="0"
              size="small"
              @change="handleCellEdit(row, 'midtermScore', row.midtermScore)"
            />
          </template>
        </el-table-column>
        <el-table-column label="期末成绩" width="120" align="center">
          <template #default="{ row }">
            <el-input-number
              v-model="row.finalScore"
              :min="0"
              :max="100"
              :precision="0"
              size="small"
              @change="handleCellEdit(row, 'finalScore', row.finalScore)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="totalScore" label="总评成绩" width="100" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.totalScore && row.totalScore < 60 ? '#F56C6C' : '#52C41A', fontWeight: 600 }">
              {{ row.totalScore ?? '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="gpa" label="绩点" width="80" align="center" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Edit" @click="openEditDialog(row)">单独修改</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog
      v-model="editDialogVisible"
      :title="`修改成绩 - ${currentStudent?.name}`"
      width="500px"
    >
      <el-form v-if="currentStudent" :model="currentStudent" label-width="100px">
        <el-form-item label="学号">
          <el-input v-model="currentStudent.studentId" disabled />
        </el-form-item>
        <el-form-item label="班级">
          <el-input v-model="currentStudent.className" disabled />
        </el-form-item>
        <el-form-item label="平均成绩">
          <el-input-number v-model="currentStudent.usualScore" disabled style="width: 100%" />
        </el-form-item>
        <el-form-item label="期中成绩">
          <el-input-number v-model="currentStudent.midtermScore" :min="0" :max="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="期末成绩">
          <el-input-number v-model="currentStudent.finalScore" :min="0" :max="100" style="width: 100%" />
        </el-form-item>
        <el-alert 
          title="平均成绩自动计算：期中与期末平均值" 
          type="info" 
          :closable="false"
          style="margin-bottom: 15px"
        />
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveStudentScore">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.teacher-grade-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.header-card {
  flex-shrink: 0;
}
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.right-section {
  display: flex;
  gap: 10px;
}
.avg-score {
  font-weight: 600;
  color: var(--primary-color);
}
.statistics-section {
  flex-shrink: 0;
}
.stat-card {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: all 0.3s;
}
.stat-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  transform: translateY(-2px);
}
.stat-content {
  text-align: center;
  padding: 10px 0;
}
.stat-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 10px;
}
.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}
.stat-value.success {
  color: #52C41A;
}
.stat-value.danger {
  color: #F56C6C;
}
.stat-value.primary {
  color: #409EFF;
}
.stat-value.warning {
  color: #E6A23C;
}
.chart-card {
  flex-shrink: 0;
}
.chart-container {
  height: 280px;
}
.table-card {
  flex: 1;
  overflow: hidden;
}
/* 教师端色彩规范 */
:deep(.el-table__body tr:hover > td) {
  background-color: rgba(255, 255, 255, 0.05) !important;
}
</style>
