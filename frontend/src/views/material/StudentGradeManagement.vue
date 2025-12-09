<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'

// --- 1. 类型定义 ---
interface ScoreDetail {
  usualScore: number    // 平时成绩（30%）
  midtermScore: number  // 期中成绩（30%）
  finalScore: number    // 期末成绩（40%）
  comment: string       // 教师评语
}

interface Score {
  id: number
  courseName: string      // 课程名称
  courseId: string        // 课程号
  credit: number          // 学分
  score: number           // 总成绩
  gpa: number             // 绩点
  assessmentType: string  // 考核方式（考试/考查）
  semester: string        // 学期（如"2023-2024-1"）
  teacherName: string     // 教师姓名
  details: ScoreDetail    // 成绩详情
}

// --- 2. 模拟数据 ---
const calculateGPA = (score: number): number => {
  if (score < 60) return 0
  return Math.max(0, Number(((score / 10) - 5).toFixed(1)))
}

const mockScores: Score[] = [
  // 2023-2024-1学期
  { 
    id: 1, courseName: '高等数学A', courseId: 'MATH101', credit: 4, score: 92, gpa: 0, 
    assessmentType: '考试', semester: '2023-2024-1', teacherName: '张教授',
    details: { usualScore: 88, midtermScore: 90, finalScore: 95, comment: '学习认真，成绩优异' }
  },
  { 
    id: 2, courseName: '大学英语', courseId: 'ENG101', credit: 3, score: 85, gpa: 0, 
    assessmentType: '考试', semester: '2023-2024-1', teacherName: '李老师',
    details: { usualScore: 82, midtermScore: 84, finalScore: 88, comment: '英语基础扎实' }
  },
  { 
    id: 3, courseName: '计算机导论', courseId: 'CS101', credit: 3, score: 78, gpa: 0, 
    assessmentType: '考查', semester: '2023-2024-1', teacherName: '王老师',
    details: { usualScore: 75, midtermScore: 78, finalScore: 80, comment: '编程能力有待提高' }
  },
  { 
    id: 4, courseName: '线性代数', courseId: 'MATH102', credit: 3, score: 88, gpa: 0, 
    assessmentType: '考试', semester: '2023-2024-1', teacherName: '赵教授',
    details: { usualScore: 85, midtermScore: 87, finalScore: 90, comment: '逻辑思维能力强' }
  },
  { 
    id: 5, courseName: '思想道德修养', courseId: 'POL101', credit: 2, score: 90, gpa: 0, 
    assessmentType: '考查', semester: '2023-2024-1', teacherName: '刘老师',
    details: { usualScore: 88, midtermScore: 90, finalScore: 92, comment: '积极参与课堂讨论' }
  },
  
  // 2023-2024-2学期
  { 
    id: 6, courseName: '数据结构', courseId: 'CS201', credit: 4, score: 82, gpa: 0, 
    assessmentType: '考试', semester: '2023-2024-2', teacherName: '陈教授',
    details: { usualScore: 80, midtermScore: 82, finalScore: 84, comment: '算法理解较好' }
  },
  { 
    id: 7, courseName: '概率论', courseId: 'MATH201', credit: 3, score: 75, gpa: 0, 
    assessmentType: '考试', semester: '2023-2024-2', teacherName: '周老师',
    details: { usualScore: 72, midtermScore: 75, finalScore: 78, comment: '需加强概率题练习' }
  },
  { 
    id: 8, courseName: '操作系统', courseId: 'CS202', credit: 3, score: 86, gpa: 0, 
    assessmentType: '考试', semester: '2023-2024-2', teacherName: '吴教授',
    details: { usualScore: 84, midtermScore: 86, finalScore: 88, comment: '系统理解深入' }
  },
  { 
    id: 9, courseName: '计算机网络', courseId: 'CS203', credit: 3, score: 80, gpa: 0, 
    assessmentType: '考查', semester: '2023-2024-2', teacherName: '郑老师',
    details: { usualScore: 78, midtermScore: 80, finalScore: 82, comment: '网络协议掌握良好' }
  },
  { 
    id: 10, courseName: '大学物理', courseId: 'PHY101', credit: 3, score: 72, gpa: 0, 
    assessmentType: '考试', semester: '2023-2024-2', teacherName: '孙教授',
    details: { usualScore: 70, midtermScore: 72, finalScore: 74, comment: '物理实验表现不错' }
  },
  { 
    id: 11, courseName: '体育', courseId: 'PE101', credit: 1, score: 88, gpa: 0, 
    assessmentType: '考查', semester: '2023-2024-2', teacherName: '钱老师',
    details: { usualScore: 86, midtermScore: 88, finalScore: 90, comment: '体育成绩优秀' }
  },
  
  // 2024-2025-1学期
  { 
    id: 12, courseName: '数据库原理', courseId: 'CS301', credit: 4, score: 90, gpa: 0, 
    assessmentType: '考试', semester: '2024-2025-1', teacherName: '黄教授',
    details: { usualScore: 88, midtermScore: 90, finalScore: 92, comment: 'SQL语句掌握出色' }
  },
  { 
    id: 13, courseName: '软件工程', courseId: 'CS302', credit: 3, score: 84, gpa: 0, 
    assessmentType: '考查', semester: '2024-2025-1', teacherName: '徐老师',
    details: { usualScore: 82, midtermScore: 84, finalScore: 86, comment: '项目开发能力强' }
  },
  { 
    id: 14, courseName: '算法设计', courseId: 'CS303', credit: 3, score: 87, gpa: 0, 
    assessmentType: '考试', semester: '2024-2025-1', teacherName: '杨教授',
    details: { usualScore: 85, midtermScore: 87, finalScore: 89, comment: '算法思维清晰' }
  },
  { 
    id: 15, courseName: '人工智能导论', courseId: 'CS304', credit: 3, score: 81, gpa: 0, 
    assessmentType: '考查', semester: '2024-2025-1', teacherName: '马老师',
    details: { usualScore: 80, midtermScore: 81, finalScore: 82, comment: 'AI理论理解透彻' }
  },
  { 
    id: 16, courseName: 'Web开发技术', courseId: 'CS305', credit: 2, score: 89, gpa: 0, 
    assessmentType: '考查', semester: '2024-2025-1', teacherName: '冯老师',
    details: { usualScore: 87, midtermScore: 89, finalScore: 91, comment: '前端开发水平高' }
  },
]

mockScores.forEach(s => s.gpa = calculateGPA(s.score))

// --- 3. 状态管理 ---
const loading = ref(false)
const currentSemester = ref('2024-2025-1')
const allScores = ref<Score[]>(mockScores)
const filteredScores = ref<Score[]>([])
const gradeFilter = ref('')
const assessmentFilter = ref('')
const detailDialogVisible = ref(false)
const currentScoreDetail = ref<Score | null>(null)
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

// 学期列表
const semesters = computed(() => {
  const set = new Set(allScores.value.map(s => s.semester))
  return Array.from(set).sort().reverse()
})

// 当前学期成绩列表
const currentSemesterScores = computed(() => {
  let scores = allScores.value.filter(s => s.semester === currentSemester.value)
  
  if (gradeFilter.value) {
    scores = scores.filter(s => getGradeLevel(s.score) === gradeFilter.value)
  }
  
  if (assessmentFilter.value) {
    scores = scores.filter(s => s.assessmentType === assessmentFilter.value)
  }
  
  return scores
})

// 统计数据
const statistics = computed(() => {
  const scores = currentSemesterScores.value
  const totalCredits = scores.reduce((sum, s) => sum + s.credit, 0)
  const earnedCredits = scores.filter(s => s.score >= 60).reduce((sum, s) => sum + s.credit, 0)
  const avgGPA = scores.length > 0 
    ? (scores.reduce((sum, s) => sum + (s.gpa || 0) * s.credit, 0) / totalCredits).toFixed(2)
    : '0.00'
  const passRate = scores.length > 0 
    ? ((scores.filter(s => s.score >= 60).length / scores.length) * 100).toFixed(1)
    : '0.0'
  
  return {
    totalCredits,
    earnedCredits,
    avgGPA,
    passRate
  }
})

// ECharts 数据
const trendData = computed(() => {
  const semesterGroups = semesters.value.map(sem => {
    const semScores = allScores.value.filter(s => s.semester === sem)
    const totalCredits = semScores.reduce((sum, s) => sum + s.credit, 0)
    const avgScore = semScores.length > 0 
      ? (semScores.reduce((sum, s) => sum + s.score, 0) / semScores.length).toFixed(1)
      : '0'
    const avgGPA = semScores.length > 0 
      ? (semScores.reduce((sum, s) => sum + (s.gpa || 0) * s.credit, 0) / totalCredits).toFixed(2)
      : '0.00'
    
    return {
      semester: sem,
      avgScore: Number(avgScore),
      avgGPA: Number(avgGPA)
    }
  })
  
  return semesterGroups.reverse()
})

// --- 4. 工具函数 ---
const getGradeLevel = (score: number): string => {
  if (score >= 90) return '优秀'
  if (score >= 80) return '良好'
  if (score >= 60) return '及格'
  return '不及格'
}

const getGradeLevelColor = (score: number): string => {
  if (score >= 80) return 'success'
  if (score < 60) return 'error'
  return 'default'
}

const viewDetail = (row: Score) => {
  currentScoreDetail.value = row
  detailDialogVisible.value = true
}

const showMessage = (msg: string, color: string = 'success') => {
  snackbarText.value = msg
  snackbarColor.value = color
  snackbar.value = true
}

const exportGrades = () => {
  showMessage(`正在导出 ${currentSemester.value} 学期成绩...（模拟）`)
  setTimeout(() => {
    showMessage('成绩导出成功！')
  }, 1000)
}

// ECharts
const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null
const trendType = ref<'score' | 'gpa'>('score')

const initChart = () => {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!chartInstance) return
  
  const option = {
    title: {
      text: trendType.value === 'score' ? '学期平均成绩趋势' : '学期平均绩点趋势',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
        color: '#303133'
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const data = params[0]
        return `${data.name}<br/>${data.seriesName}: ${data.value}`
      }
    },
    xAxis: {
      type: 'category',
      data: trendData.value.map(d => d.semester),
      axisLabel: {
        rotate: 30
      }
    },
    yAxis: {
      type: 'value',
      name: trendType.value === 'score' ? '平均成绩' : '平均绩点',
      min: trendType.value === 'score' ? 60 : 0,
      max: trendType.value === 'score' ? 100 : 4.5
    },
    series: [{
      name: trendType.value === 'score' ? '平均成绩' : '平均绩点',
      type: 'line',
      data: trendData.value.map(d => trendType.value === 'score' ? d.avgScore : d.avgGPA),
      smooth: true,
      itemStyle: {
        color: '#1867C0' // Vuetify primary colorish
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{
            offset: 0, color: 'rgba(24, 103, 192, 0.3)'
          }, {
            offset: 1, color: 'rgba(24, 103, 192, 0.05)'
          }]
        }
      }
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

const toggleTrendType = () => {
  trendType.value = trendType.value === 'score' ? 'gpa' : 'score'
  updateChart()
}

const loadData = () => {
  loading.value = true
  setTimeout(() => {
    filteredScores.value = currentSemesterScores.value
    loading.value = false
  }, 500)
}

// Headers for v-data-table
const headers: any[] = [
  { title: '课程名称', key: 'courseName', align: 'start' },
  { title: '课程号', key: 'courseId', align: 'start' },
  { title: '学分', key: 'credit', align: 'center' },
  { title: '成绩', key: 'score', align: 'center' },
  { title: '绩点', key: 'gpa', align: 'center' },
  { title: '考核方式', key: 'assessmentType', align: 'center' },
  { title: '教师', key: 'teacherName', align: 'start' },
  { title: '成绩等级', key: 'gradeLevel', align: 'center' },
  { title: '操作', key: 'actions', align: 'end', sortable: false },
]

onMounted(() => {
  loadData()
  nextTick(() => {
    initChart()
    // Resize chart on window resize
    window.addEventListener('resize', () => {
      chartInstance?.resize()
    })
  })
})

// Watch for data changes to reload chart if needed, though here data is static-ish
watch(trendType, updateChart)
</script>

<template>
  <v-container fluid class="pa-4">
    <!-- 顶部操作栏 -->
    <v-card class="mb-4" elevation="1">
      <v-card-text class="d-flex align-center flex-wrap gap-4">
        <v-select
          v-model="currentSemester"
          :items="semesters"
          label="选择学期"
          density="compact"
          variant="outlined"
          hide-details
          style="max-width: 200px; margin-right: 16px;"
          @update:model-value="loadData"
        ></v-select>
        
        <v-select
          v-model="gradeFilter"
          :items="['优秀', '良好', '及格', '不及格']"
          label="成绩等级"
          density="compact"
          variant="outlined"
          clearable
          hide-details
          style="max-width: 150px; margin-right: 16px;"
          @update:model-value="loadData"
        ></v-select>
        
        <v-select
          v-model="assessmentFilter"
          :items="['考试', '考查']"
          label="考核方式"
          density="compact"
          variant="outlined"
          clearable
          hide-details
          style="max-width: 150px;"
          @update:model-value="loadData"
        ></v-select>
        
        <v-spacer></v-spacer>
        
        <v-btn
          color="primary"
          prepend-icon="mdi-download"
          @click="exportGrades"
        >
          导出成绩
        </v-btn>
      </v-card-text>
    </v-card>

    <!-- 成绩概览 -->
    <v-row class="mb-4">
      <v-col cols="12" sm="6" md="3">
        <v-card elevation="2" class="text-center fill-height">
          <v-card-text>
            <div class="text-subtitle-1 text-medium-emphasis mb-2">总学分</div>
            <div class="text-h4 font-weight-bold">{{ statistics.totalCredits }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card elevation="2" class="text-center fill-height">
          <v-card-text>
            <div class="text-subtitle-1 text-medium-emphasis mb-2">已修学分</div>
            <div class="text-h4 font-weight-bold">{{ statistics.earnedCredits }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card elevation="2" class="text-center fill-height">
          <v-card-text>
            <div class="text-subtitle-1 text-medium-emphasis mb-2">平均绩点</div>
            <div class="text-h4 font-weight-bold text-primary">{{ statistics.avgGPA }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card elevation="2" class="text-center fill-height">
          <v-card-text>
            <div class="text-subtitle-1 text-medium-emphasis mb-2">及格率</div>
            <div class="text-h4 font-weight-bold text-success">{{ statistics.passRate }}%</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 成绩趋势图 -->
    <v-card class="mb-4" elevation="1">
      <v-card-title class="d-flex justify-space-between align-center">
        <span>成绩趋势分析</span>
        <v-btn
          variant="text"
          color="primary"
          size="small"
          @click="toggleTrendType"
        >
          切换为{{ trendType === 'score' ? '绩点' : '成绩' }}视角
        </v-btn>
      </v-card-title>
      <v-card-text>
        <div ref="chartRef" style="height: 350px; width: 100%;"></div>
      </v-card-text>
    </v-card>

    <!-- 成绩列表 -->
    <v-card elevation="1">
      <v-card-title>成绩列表</v-card-title>
      <v-data-table
        :headers="headers"
        :items="currentSemesterScores"
        :loading="loading"
        item-value="id"
      >
        <template #item.score="{ item }">
          <span :class="{'text-success font-weight-bold': item.score >= 80, 'text-error font-weight-bold': item.score < 60}">
            {{ item.score }}
          </span>
        </template>
        
        <template #item.gradeLevel="{ item }">
          <v-chip
            :color="getGradeLevelColor(item.score)"
            size="small"
            variant="flat"
            class="font-weight-medium"
          >
            {{ getGradeLevel(item.score) }}
          </v-chip>
        </template>

        <template #item.actions="{ item }">
          <v-btn
            icon
            variant="text"
            color="primary"
            size="small"
            @click="viewDetail(item)"
          >
            <v-icon>mdi-eye</v-icon>
            <v-tooltip activator="parent" location="top">查看详情</v-tooltip>
          </v-btn>
        </template>
      </v-data-table>
    </v-card>

    <!-- 成绩详情弹窗 -->
    <v-dialog v-model="detailDialogVisible" max-width="700">
      <v-card v-if="currentScoreDetail">
        <v-card-title class="text-h5 bg-primary text-white">
          {{ currentScoreDetail.courseName }} - 成绩详情
        </v-card-title>
        <v-card-text class="pt-4">
          <v-table density="compact" class="mb-4 border">
            <tbody>
              <tr>
                <th class="font-weight-bold bg-grey-lighten-4">课程号</th>
                <td>{{ currentScoreDetail.courseId }}</td>
                <th class="font-weight-bold bg-grey-lighten-4">学分</th>
                <td>{{ currentScoreDetail.credit }}</td>
              </tr>
              <tr>
                <th class="font-weight-bold bg-grey-lighten-4">教师</th>
                <td>{{ currentScoreDetail.teacherName }}</td>
                <th class="font-weight-bold bg-grey-lighten-4">考核方式</th>
                <td>{{ currentScoreDetail.assessmentType }}</td>
              </tr>
              <tr>
                <th class="font-weight-bold bg-grey-lighten-4">学期</th>
                <td colspan="3">{{ currentScoreDetail.semester }}</td>
              </tr>
            </tbody>
          </v-table>

          <div class="mb-4">
            <h3 class="text-h6 mb-2">成绩构成</h3>
            <v-alert
              type="info"
              variant="tonal"
              border="start"
              class="mb-3"
              density="compact"
            >
              平时成绩（30%）包含考勤、作业、课堂表现；期中成绩（30%）；期末成绩（40%）
            </v-alert>

            <v-row>
              <v-col cols="4">
                <v-card variant="outlined" class="text-center pa-2">
                  <div class="text-caption text-grey">平时成绩 (30%)</div>
                  <div class="text-h5 font-weight-bold">{{ currentScoreDetail.details.usualScore }}</div>
                </v-card>
              </v-col>
              <v-col cols="4">
                <v-card variant="outlined" class="text-center pa-2">
                  <div class="text-caption text-grey">期中成绩 (30%)</div>
                  <div class="text-h5 font-weight-bold">{{ currentScoreDetail.details.midtermScore }}</div>
                </v-card>
              </v-col>
              <v-col cols="4">
                <v-card variant="outlined" class="text-center pa-2">
                  <div class="text-caption text-grey">期末成绩 (40%)</div>
                  <div class="text-h5 font-weight-bold">{{ currentScoreDetail.details.finalScore }}</div>
                </v-card>
              </v-col>
            </v-row>

            <div class="d-flex align-center justify-center mt-4 bg-grey-lighten-5 pa-3 rounded">
              <span class="text-h6 mr-2">总成绩：</span>
              <span :class="`text-h4 font-weight-bold text-${getGradeLevelColor(currentScoreDetail.score)}`">
                {{ currentScoreDetail.score }}
              </span>
              <span class="text-h6 ml-6 mr-2">绩点：</span>
              <span class="text-h5 font-weight-bold text-primary">
                {{ currentScoreDetail.gpa }}
              </span>
            </div>
          </div>

          <div>
            <h3 class="text-h6 mb-2">教师评语</h3>
            <v-textarea
              v-model="currentScoreDetail.details.comment"
              readonly
              variant="outlined"
              rows="3"
              hide-details
            ></v-textarea>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" variant="text" @click="detailDialogVisible = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
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
</style>
