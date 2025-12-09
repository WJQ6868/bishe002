<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import * as echarts from 'echarts'

// --- 1. 类型定义 ---
interface StudentScore {
  id: number
  studentId: string
  name: string
  className: string
  usualScore: number | null
  midtermScore: number | null
  finalScore: number | null
  totalScore: number | null
  gpa: number | null
}

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

const generateStudents = (): StudentScore[] => {
  const students: StudentScore[] = []
  for (let i = 1; i <= 30; i++) {
    const hasScore = i <= 20
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
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

// ECharts
const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

// --- 4. 核心逻辑 ---

const showMessage = (msg: string, color: string = 'success') => {
  snackbarText.value = msg
  snackbarColor.value = color
  snackbar.value = true
}

const calculateTotalScore = (student: StudentScore) => {
  if (student.usualScore !== null && student.midtermScore !== null && student.finalScore !== null) {
    student.totalScore = Math.round(
      Number(student.usualScore) * 0.3 + Number(student.midtermScore) * 0.3 + Number(student.finalScore) * 0.4
    )
    student.gpa = student.totalScore < 60 ? 0 : Number(((student.totalScore / 10) - 5).toFixed(1))
  } else {
    student.totalScore = null
    student.gpa = null
  }
}

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

const handleCellEdit = (row: StudentScore) => {
  calculateTotalScore(row)
  hasUnsavedChanges.value = true
}

const openEditDialog = (student: StudentScore) => {
  currentStudent.value = JSON.parse(JSON.stringify(student)) // Deep copy
  editDialogVisible.value = true
}

const saveStudentScore = () => {
  if (!currentStudent.value) return
  
  const index = studentScores.value.findIndex(s => s.id === currentStudent.value!.id)
  if (index !== -1) {
    calculateTotalScore(currentStudent.value)
    studentScores.value[index] = { ...currentStudent.value }
    hasUnsavedChanges.value = true
    editDialogVisible.value = false
    showMessage('成绩修改成功')
    updateChart()
  }
}

const handleImport = () => {
  showMessage('模拟导入成功！已导入30条成绩记录')
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

const handleExport = () => {
  showMessage('正在导出成绩表...（模拟）')
  setTimeout(() => {
    showMessage('成绩表导出成功！')
  }, 1000)
}

const saveAllScores = () => {
  loading.value = true
  setTimeout(() => {
    localStorage.setItem('teacher_scores', JSON.stringify(studentScores.value))
    hasUnsavedChanges.value = false
    loading.value = false
    showMessage('成绩保存成功')
  }, 500)
}

const initChart = () => {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

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
      axisPointer: { type: 'shadow' }
    },
    xAxis: {
      type: 'category',
      data: ['0-59分', '60-69分', '70-79分', '80-89分', '90-100分'],
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
      itemStyle: { color: '#4CAF50' }, // Green 500
      label: { show: true, position: 'top' }
    }],
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    }
  }
  
  chartInstance.setOption(option)
}

const loadLocalData = () => {
  const saved = localStorage.getItem('teacher_scores')
  if (saved) {
    studentScores.value = JSON.parse(saved)
  } else {
    studentScores.value.forEach(s => calculateTotalScore(s))
  }
}

// Headers for data table
const headers: any[] = [
  { title: '学号', key: 'studentId', align: 'start', fixed: true },
  { title: '姓名', key: 'name', align: 'start', fixed: true },
  { title: '班级', key: 'className', align: 'start' },
  { title: '平时成绩', key: 'usualScore', align: 'center', width: '120px' },
  { title: '期中成绩', key: 'midtermScore', align: 'center', width: '120px' },
  { title: '期末成绩', key: 'finalScore', align: 'center', width: '120px' },
  { title: '总评成绩', key: 'totalScore', align: 'center' },
  { title: '绩点', key: 'gpa', align: 'center' },
  { title: '操作', key: 'actions', align: 'center', fixed: true },
]

onMounted(() => {
  loadLocalData()
  nextTick(() => {
    initChart()
    window.addEventListener('resize', () => chartInstance?.resize())
  })
})
</script>

<template>
  <v-container fluid class="pa-4 h-100 d-flex flex-column">
    <!-- 顶部操作栏 -->
    <v-card class="mb-4 flex-shrink-0" elevation="1">
      <v-card-text class="d-flex align-center flex-wrap gap-4">
        <div class="d-flex align-center gap-2">
          <span class="text-body-1 font-weight-medium">选择课程：</span>
          <v-select
            v-model="selectedCourse"
            :items="courses"
            item-title="name"
            item-value="id"
            variant="outlined"
            density="compact"
            hide-details
            style="width: 250px;"
          >
            <template v-slot:item="{ props, item }">
              <v-list-item v-bind="props" :subtitle="item.raw.semester"></v-list-item>
            </template>
            <template v-slot:selection="{ item }">
              {{ item.title }} ({{ item.raw.semester }})
            </template>
          </v-select>
        </div>
        
        <v-spacer></v-spacer>
        
        <div class="d-flex align-center gap-2">
          <v-btn prepend-icon="mdi-upload" @click="handleImport">批量导入</v-btn>
          <v-btn prepend-icon="mdi-download" @click="handleExport">批量导出</v-btn>
          <v-btn 
            color="success" 
            prepend-icon="mdi-check" 
            :disabled="!hasUnsavedChanges"
            :loading="loading"
            @click="saveAllScores"
          >
            保存成绩
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <!-- 成绩统计 -->
    <v-row class="mb-4 flex-shrink-0">
      <v-col cols="6" sm="4" md="2">
        <v-card elevation="1" class="text-center fill-height">
          <v-card-text>
            <div class="text-caption text-grey mb-1">平均分</div>
            <div class="text-h5 font-weight-bold">{{ statistics.average }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="4" md="2">
        <v-card elevation="1" class="text-center fill-height">
          <v-card-text>
            <div class="text-caption text-grey mb-1">最高分</div>
            <div class="text-h5 font-weight-bold text-success">{{ statistics.highest }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="4" md="2">
        <v-card elevation="1" class="text-center fill-height">
          <v-card-text>
            <div class="text-caption text-grey mb-1">最低分</div>
            <div class="text-h5 font-weight-bold text-error">{{ statistics.lowest }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="6" md="3">
        <v-card elevation="1" class="text-center fill-height">
          <v-card-text>
            <div class="text-caption text-grey mb-1">及格率</div>
            <div class="text-h5 font-weight-bold text-primary">{{ statistics.passRate }}%</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card elevation="1" class="text-center fill-height">
          <v-card-text>
            <div class="text-caption text-grey mb-1">优秀率</div>
            <div class="text-h5 font-weight-bold text-warning">{{ statistics.excellentRate }}%</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 成绩分布图 -->
    <v-card class="mb-4 flex-shrink-0" elevation="1">
      <v-card-text>
        <div ref="chartRef" style="height: 250px; width: 100%;"></div>
      </v-card-text>
    </v-card>

    <!-- 成绩列表 -->
    <v-card class="flex-grow-1 d-flex flex-column" elevation="1" style="overflow: hidden;">
      <v-card-title>学生成绩列表 ({{ studentScores.length }}人)</v-card-title>
      <v-data-table
        :headers="headers"
        :items="studentScores"
        class="flex-grow-1 overflow-y-auto"
        fixed-header
        items-per-page="-1"
        :sort-by="[{ key: 'studentId', order: 'asc' }]"
      >
        <!-- Editable columns -->
        <template v-slot:item.usualScore="{ item }">
          <v-text-field
            v-model.number="item.usualScore"
            type="number"
            variant="underlined"
            density="compact"
            hide-details
            min="0"
            max="100"
            class="centered-input"
            @update:model-value="handleCellEdit(item)"
          ></v-text-field>
        </template>
        <template v-slot:item.midtermScore="{ item }">
          <v-text-field
            v-model.number="item.midtermScore"
            type="number"
            variant="underlined"
            density="compact"
            hide-details
            min="0"
            max="100"
            class="centered-input"
            @update:model-value="handleCellEdit(item)"
          ></v-text-field>
        </template>
        <template v-slot:item.finalScore="{ item }">
          <v-text-field
            v-model.number="item.finalScore"
            type="number"
            variant="underlined"
            density="compact"
            hide-details
            min="0"
            max="100"
            class="centered-input"
            @update:model-value="handleCellEdit(item)"
          ></v-text-field>
        </template>
        
        <template v-slot:item.totalScore="{ item }">
          <span :class="item.totalScore && item.totalScore < 60 ? 'text-error font-weight-bold' : 'text-success font-weight-bold'">
            {{ item.totalScore ?? '-' }}
          </span>
        </template>
        
        <template v-slot:item.actions="{ item }">
          <v-btn
            variant="text"
            color="primary"
            size="small"
            prepend-icon="mdi-pencil"
            @click="openEditDialog(item)"
          >
            修改
          </v-btn>
        </template>
        
        <!-- Bottom slot to hide pagination controls if we want infinite scroll feel or just list all -->
        <template v-slot:bottom></template>
      </v-data-table>
    </v-card>

    <!-- 编辑弹窗 -->
    <v-dialog v-model="editDialogVisible" max-width="500">
      <v-card v-if="currentStudent">
        <v-card-title class="text-h5">修改成绩 - {{ currentStudent.name }}</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="6">
              <v-text-field label="学号" v-model="currentStudent.studentId" readonly variant="filled"></v-text-field>
            </v-col>
            <v-col cols="6">
              <v-text-field label="班级" v-model="currentStudent.className" readonly variant="filled"></v-text-field>
            </v-col>
            <v-col cols="12">
              <v-text-field 
                label="平时成绩" 
                v-model.number="currentStudent.usualScore" 
                type="number"
                variant="outlined"
                min="0" max="100"
              ></v-text-field>
            </v-col>
            <v-col cols="12">
              <v-text-field 
                label="期中成绩" 
                v-model.number="currentStudent.midtermScore" 
                type="number"
                variant="outlined"
                min="0" max="100"
              ></v-text-field>
            </v-col>
            <v-col cols="12">
              <v-text-field 
                label="期末成绩" 
                v-model.number="currentStudent.finalScore" 
                type="number"
                variant="outlined"
                min="0" max="100"
              ></v-text-field>
            </v-col>
          </v-row>
          
          <v-alert
            type="info"
            variant="tonal"
            border="start"
            density="compact"
            class="mt-2"
          >
            总评成绩计算公式：平时30% + 期中30% + 期末40%
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey-darken-1" variant="text" @click="editDialogVisible = false">取消</v-btn>
          <v-btn color="primary" variant="text" @click="saveStudentScore">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar -->
    <v-snackbar
      v-model="snackbar"
      :color="snackbarColor"
      timeout="3000"
      location="top"
    >
      {{ snackbarText }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<style scoped>
.gap-4 {
  gap: 16px;
}
.gap-2 {
  gap: 8px;
}
.h-100 {
  height: 100% !important;
}
.flex-grow-1 {
  flex-grow: 1 !important;
}
.flex-shrink-0 {
  flex-shrink: 0 !important;
}
/* Center text in inputs inside table */
:deep(.centered-input input) {
  text-align: center;
}
</style>
