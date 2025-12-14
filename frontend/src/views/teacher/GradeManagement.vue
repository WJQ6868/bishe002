<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Download, Check, Edit } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

// --- 1. 类型定义 ---
/**
 * 学生成绩记录
 */
interface StudentScore {
  id: number
  studentId: string
  name: string
  className: string
  usualScore: number | null      // 平时成绩
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

// --- 2. 模拟数据 ---
const courses = [
  { id: 1, name: 'Python编程', semester: '2024-2025-1' },
  { id: 2, name: '数据结构', semester: '2024-2025-1' },
  { id: 3, name: 'Web开发', semester: '2024-2025-1' }
]

// 生成30名学生的模拟数据
const generateStudents = (): StudentScore[] => {
  const students: StudentScore[] = []
  for (let i = 1; i <= 30; i++) {
    const hasScore = i <= 20 // 前20个学生已有成绩
    students.push({
      id: i,
      studentId: `2023${String(i).padStart(4, '0')}`,
      name: `学生${i}`,
      className: `计算机${(i % 3) + 1}班`,
      usualScore: hasScore ? Math.floor(Math.random() * 20 + 70) : null,
      midtermScore: hasScore ? Math.floor(Math.random() * 20 + 70) : null,
      finalScore: hasScore ? Math.floor(Math.random() * 20 + 70) : null,
      totalScore: null,
      gpa: null
    })
  }
  return students
}

// --- 3. 状态管理 ---
const selectedCourse = ref(1)
const studentScores = ref<StudentScore[]>(generateStudents())
const loading = ref(false)
const hasUnsavedChanges = ref(false)
const editDialogVisible = ref(false)
const currentStudent = ref<StudentScore | null>(null)

// ECharts图表
const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

// --- 4. 核心逻辑 ---

/**
 * 计算总评成绩
 * 公式：总评 = 平时30% + 期中30% + 期末40%
 */
const calculateTotalScore = (student: StudentScore) => {
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
const handleCellEdit = (row: StudentScore, field: 'usualScore' | 'midtermScore' | 'finalScore', value: number) => {
  row[field] = value
  calculateTotalScore(row)
  hasUnsavedChanges.value = true
}

// 打开编辑弹窗
const openEditDialog = (student: StudentScore) => {
  currentStudent.value = { ...student }
  editDialogVisible.value = true
}

// 保存单个学生成绩
const saveStudentScore = () => {
  if (!currentStudent.value) return
  
  const index = studentScores.value.findIndex(s => s.id === currentStudent.value!.id)
  if (index !== -1) {
    calculateTotalScore(currentStudent.value)
    studentScores.value[index] = { ...currentStudent.value }
    hasUnsavedChanges.value = true
    editDialogVisible.value = false
    ElMessage.success('成绩修改成功')
  }
}

// 批量导入
const handleImport = () => {
  ElMessage.success('模拟导入成功！已导入30条成绩记录')
  // 模拟填充所有学生成绩
  studentScores.value.forEach(student => {
    if (student.usualScore === null) {
      student.usualScore = Math.floor(Math.random() * 20 + 70)
      student.midtermScore = Math.floor(Math.random() * 20 + 70)
      student.finalScore = Math.floor(Math.random() * 20 + 70)
      calculateTotalScore(student)
    }
  })
  hasUnsavedChanges.value = true
  updateChart()
}

// 批量导出
const handleExport = () => {
  ElMessage.success('正在导出成绩表...（模拟）')
  setTimeout(() => {
    ElMessage.success('成绩表导出成功！')
  }, 1000)
}

// 保存成绩
const saveAllScores = () => {
  loading.value = true
  setTimeout(() => {
    localStorage.setItem('teacher_scores', JSON.stringify(studentScores.value))
    hasUnsavedChanges.value = false
    loading.value = false
    ElMessage.success('成绩保存成功')
  }, 500)
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
    title: {
      text: '成绩分布统计',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
        color: '#303133'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'category',
      data: ['0-59分', '60-69分', '70-79分', '80-89分', '90-100分'],
      axisLabel: {
        rotate: 0
      }
    },
    yAxis: {
      type: 'value',
      name: '人数',
      minInterval: 1
    },
    series: [{
      name: '人数',
      type: 'bar',
      data: Object.values(dist),
      itemStyle: {
        color: '#52C41A'
      },
      label: {
        show: true,
        position: 'top'
      }
    }]
  }
  
  chartInstance.setOption(option)
}

// 加载本地数据
const loadLocalData = () => {
  const saved = localStorage.getItem('teacher_scores')
  if (saved) {
    studentScores.value = JSON.parse(saved)
  }
}

loadLocalData()

// 初始化图表
nextTick(() => {
  initChart()
})

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
          <el-select v-model="selectedCourse" style="width: 200px">
            <el-option v-for="course in courses" :key="course.id" :label="`${course.name} (${course.semester})`" :value="course.id" />
          </el-select>
        </div>
        <div class="right-section">
          <el-button :icon="Upload" @click="handleImport">批量导入</el-button>
          <el-button :icon="Download" @click="handleExport">批量导出</el-button>
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
        :data="studentScores"
        style="width: 100%"
        border
        height="520"
      >
        <el-table-column prop="studentId" label="学号" width="120" fixed />
        <el-table-column prop="name" label="姓名" width="100" fixed />
        <el-table-column prop="className" label="班级" width="120" />
        <el-table-column label="平时成绩" width="120" align="center">
          <template #default="{ row }">
            <el-input-number
              v-model="row.usualScore"
              :min="0"
              :max="100"
              :precision="0"
              size="small"
              @change="handleCellEdit(row, 'usualScore', row.usualScore)"
            />
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
        <el-form-item label="平时成绩">
          <el-input-number v-model="currentStudent.usualScore" :min="0" :max="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="期中成绩">
          <el-input-number v-model="currentStudent.midtermScore" :min="0" :max="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="期末成绩">
          <el-input-number v-model="currentStudent.finalScore" :min="0" :max="100" style="width: 100%" />
        </el-form-item>
        <el-alert 
          title="总评成绩计算公式：平时30% + 期中30% + 期末40%" 
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
  height: 240px;
}
.table-card {
  flex: 1;
  overflow: hidden;
}
/* 教师端色彩规范 */
:deep(.el-table__body tr:hover > td) {
  background-color: #F0F9EB !important;
}
</style>
