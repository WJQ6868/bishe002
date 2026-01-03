<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, View } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  useStudentGrades,
  getGradeLevel,
  getGradeLevelColor,
  type StudentGradeRecord,
} from '@/composables/useStudentGrades'

const { grades, loading } = useStudentGrades()
const currentSemester = ref('')
const gradeFilter = ref('')
const assessmentFilter = ref('')
const detailDialogVisible = ref(false)
const currentScoreDetail = ref<StudentGradeRecord | null>(null)
const trendType = ref<'score' | 'gpa'>('score')

const semesters = computed(() => {
  const set = new Set(grades.value.map((g) => g.semester))
  return Array.from(set).sort().reverse()
})

watch(semesters, (list) => {
  if (!currentSemester.value && list.length) {
    currentSemester.value = list[0]
  }
})

const semesterGrades = computed(() => {
  const targetSemester = currentSemester.value || semesters.value[0] || ''
  let list = grades.value.filter((g) => g.semester === targetSemester)
  if (gradeFilter.value) {
    list = list.filter((g) => getGradeLevel(g.score) === gradeFilter.value)
  }
  if (assessmentFilter.value) {
    list = list.filter((g) => g.assessmentType === assessmentFilter.value)
  }
  return list
})

const statistics = computed(() => {
  const list = semesterGrades.value
  const totalCredits = list.reduce((sum, item) => sum + item.credit, 0)
  const earnedCredits = list.filter((item) => item.score >= 60).reduce((sum, item) => sum + item.credit, 0)
  const avgGPA = totalCredits > 0
    ? (list.reduce((sum, item) => sum + item.gpa * item.credit, 0) / totalCredits).toFixed(2)
    : '0.00'
  const passRate = list.length > 0
    ? ((list.filter((item) => item.score >= 60).length / list.length) * 100).toFixed(1)
    : '0.0'
  return {
    totalCredits,
    earnedCredits,
    avgGPA,
    passRate,
  }
})

const trendData = computed(() => {
  const bySemester: Record<string, StudentGradeRecord[]> = {}
  grades.value.forEach((record) => {
    if (!bySemester[record.semester]) {
      bySemester[record.semester] = []
    }
    bySemester[record.semester].push(record)
  })
  return Object.keys(bySemester)
    .sort()
    .map((semester) => {
      const list = bySemester[semester]
      const avgScore = list.length ? (list.reduce((sum, item) => sum + item.score, 0) / list.length).toFixed(1) : '0'
      const totalCredits = list.reduce((sum, item) => sum + item.credit, 0)
      const avgGPA = totalCredits > 0
        ? (list.reduce((sum, item) => sum + item.gpa * item.credit, 0) / totalCredits).toFixed(2)
        : '0.00'
      return {
        semester,
        avgScore: Number(avgScore),
        avgGPA: Number(avgGPA),
      }
    })
})

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

const initChart = () => {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!chartInstance) return
  const xData = trendData.value.map((item) => item.semester)
  const seriesData = trendData.value.map((item) => (trendType.value === 'score' ? item.avgScore : item.avgGPA))
  chartInstance.setOption({
    backgroundColor: 'transparent',
    title: {
      text: trendType.value === 'score' ? '成绩趋势图' : '绩点趋势图',
      left: 'center',
      textStyle: { fontSize: 16, fontWeight: 600, color: '#fff' },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(20, 20, 20, 0.9)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: { color: '#fff' },
      formatter: (params: any) => {
        const data = params[0]
        return `${data.name}<br/>${data.seriesName}: ${data.value}` 
      },
    },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { rotate: 30, color: 'rgba(255,255,255,0.7)' },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } }
    },
    yAxis: {
      type: 'value',
      name: trendType.value === 'score' ? '成绩' : '绩点',
      min: trendType.value === 'score' ? 60 : 0,
      max: trendType.value === 'score' ? 100 : 4.5,
      axisLabel: { color: 'rgba(255,255,255,0.7)' },
      nameTextStyle: { color: 'rgba(255,255,255,0.7)' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }
    },
    series: [{
      name: trendType.value === 'score' ? '成绩' : '绩点',
      type: 'line',
      data: seriesData,
      smooth: true,
      itemStyle: { color: '#00f2fe' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(0, 242, 254, 0.3)' },
            { offset: 1, color: 'rgba(0, 242, 254, 0.05)' },
          ],
        },
      },
    }],
    toolbox: {
      feature: { saveAsImage: { title: '保存图片' } },
      iconStyle: { borderColor: '#fff' }
    },
  })
}

watch([trendData, trendType], () => updateChart())

onMounted(() => {
  initChart()
  if (semesters.value.length) {
    currentSemester.value = semesters.value[0]
  }
})

const toggleTrendType = () => {
  trendType.value = trendType.value === 'score' ? 'gpa' : 'score'
  updateChart()
}

const viewDetail = (row: StudentGradeRecord) => {
  currentScoreDetail.value = row
  detailDialogVisible.value = true
}

const exportGrades = () => {
  ElMessage.success('正在导出...')
  setTimeout(() => {
    ElMessage.success('导出成功')
  }, 800)
}
</script>

<template>
  <div class="grade-management-container">
    <!-- 顶部操作栏 -->
    <el-card class="header-card">
      <div class="header-bar">
        <div class="left-filters">
          <el-select v-model="currentSemester" placeholder="选择学期" style="width: 180px">
            <el-option v-for="sem in semesters" :key="sem" :label="sem" :value="sem" />
          </el-select>
          <el-select v-model="gradeFilter" placeholder="成绩等级" style="width: 120px; margin-left: 10px" clearable>
            <el-option label="优秀" value="优秀" />
            <el-option label="良好" value="良好" />
            <el-option label="及格" value="及格" />
            <el-option label="不及格" value="不及格" />
          </el-select>
          <el-select v-model="assessmentFilter" placeholder="考核方式" style="width: 120px; margin-left: 10px" clearable>
            <el-option label="考试" value="考试" />
            <el-option label="考查" value="考查" />
          </el-select>
        </div>
        <el-button type="primary" @click="exportGrades">
          <el-icon><Download /></el-icon>
          导出成绩
        </el-button>
      </div>
    </el-card>

    <!-- 成绩概览 -->
    <div class="overview-section">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-label">总学分</div>
              <div class="stat-value">{{ statistics.totalCredits }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-label">已修学分</div>
              <div class="stat-value">{{ statistics.earnedCredits }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-label">平均绩点</div>
              <div class="stat-value primary">{{ statistics.avgGPA }}</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-label">及格率</div>
              <div class="stat-value success">{{ statistics.passRate }}%</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 成绩趋势图 -->
    <el-card class="chart-card">
      <template #header>
        <div class="chart-header">
          <span>成绩趋势分析</span>
          <el-button size="small" @click="toggleTrendType">
            切换为{{ trendType === 'score' ? '绩点' : '成绩' }}视角
          </el-button>
        </div>
      </template>
      <div ref="chartRef" class="chart-container"></div>
    </el-card>

    <!-- 成绩列表 -->
    <el-card class="table-card">
      <template #header>
        <span>成绩列表</span>
      </template>
      <el-table
        v-loading="loading"
        :data="semesterGrades"
        style="width: 100%"
        :row-class-name="(scope: any) => scope.row.score < 60 ? 'fail-row' : ''"
      >
        <el-table-column prop="courseName" label="课程名称" min-width="150" />
        <el-table-column prop="courseId" label="课程号" width="120" />
        <el-table-column prop="credit" label="学分" width="80" align="center" />
        <el-table-column prop="score" label="成绩" width="80" align="center">
          <template #default="{ row }">
            <span :style="{ color: getGradeLevelColor(row.score), fontWeight: 600 }">
              {{ row.score }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="gpa" label="绩点" width="80" align="center" />
        <el-table-column prop="assessmentType" label="考核方式" width="100" align="center" />
        <el-table-column prop="teacherName" label="教师" width="100" />
        <el-table-column label="成绩等级" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.score >= 90 ? 'success' : row.score >= 80 ? 'primary' : row.score >= 60 ? 'info' : 'danger'">
              {{ getGradeLevel(row.score) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetail(row)">
              <el-icon><View /></el-icon>
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 成绩详情弹窗 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="`${currentScoreDetail?.courseName} - 成绩详情`"
      width="600px"
    >
      <div v-if="currentScoreDetail" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="课程号">{{ currentScoreDetail.courseId }}</el-descriptions-item>
          <el-descriptions-item label="学分">{{ currentScoreDetail.credit }}</el-descriptions-item>
          <el-descriptions-item label="教师">{{ currentScoreDetail.teacherName }}</el-descriptions-item>
          <el-descriptions-item label="考核方式">{{ currentScoreDetail.assessmentType }}</el-descriptions-item>
          <el-descriptions-item label="学期" :span="2">{{ currentScoreDetail.semester }}</el-descriptions-item>
        </el-descriptions>
        
        <div class="score-composition">
          <h4>成绩构成</h4>
          <el-alert 
            title="成绩构成说明" 
            type="info" 
            :closable="false"
            style="margin-bottom: 15px"
          >
            平时成绩（30%）包含考勤、作业、课堂表现；期中成绩（30%）；期末成绩（40%）
          </el-alert>
          <el-row :gutter="15">
            <el-col :span="8">
              <div class="composition-item">
                <div class="comp-label">平时成绩（30%）</div>
                <div class="comp-value">{{ currentScoreDetail.details.usualScore }}</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="composition-item">
                <div class="comp-label">期中成绩（30%）</div>
                <div class="comp-value">{{ currentScoreDetail.details.midtermScore }}</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="composition-item">
                <div class="comp-label">期末成绩（40%）</div>
                <div class="comp-value">{{ currentScoreDetail.details.finalScore }}</div>
              </div>
            </el-col>
          </el-row>
          <div class="final-score">
            <span>总成绩：</span>
            <span :style="{ color: getGradeLevelColor(currentScoreDetail.score), fontSize: '24px', fontWeight: 'bold' }">
              {{ currentScoreDetail.score }}
            </span>
            <span style="margin-left: 20px">绩点：</span>
            <span style="font-size: 20px; font-weight: bold; color: #00f2fe">
              {{ currentScoreDetail.gpa }}
            </span>
          </div>
        </div>
        
        <div class="teacher-comment">
          <h4>教师评语</h4>
          <el-input
            v-model="currentScoreDetail.details.comment"
            type="textarea"
            :rows="3"
            readonly
            style="font-size: 14px"
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.grade-management-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 40px;
  color: #fff;
}

.header-card, .chart-card, .table-card {
  background: var(--card-bg) !important;
  backdrop-filter: blur(10px) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 12px !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
}

.header-card {
  flex-shrink: 0;
}
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.overview-section {
  flex-shrink: 0;
}
.stat-card {
  background: var(--card-bg) !important;
  backdrop-filter: blur(10px) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 12px !important;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  border-color: var(--primary-color) !important;
}

.stat-content {
  text-align: center;
  padding: 10px 0;
}

.stat-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 10px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #fff;
}

.stat-value.primary {
  color: #00f2fe;
}

.stat-value.success {
  color: #67c23a;
}

.chart-card {
  flex-shrink: 0;
}
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #fff;
}

.chart-container {
  height: 300px;
}

.table-card {
  overflow: visible;
}

:deep(.el-table) {
  background-color: transparent !important;
  color: #fff !important;
}

:deep(.el-table__row) {
  background-color: transparent !important;
}

:deep(.el-table th.el-table__cell) {
  background-color: rgba(255, 255, 255, 0.05) !important;
  color: #00f2fe !important;
}

:deep(.el-table .fail-row) {
  background: rgba(245, 108, 108, 0.1) !important;
}

:deep(.el-table__body tr:hover > td) {
  background-color: rgba(0, 242, 254, 0.1) !important;
}

.detail-content {
  padding: 10px 0;
  color: #fff;
}

.score-composition {
  margin-top: 25px;
}

.score-composition h4, .teacher-comment h4 {
  margin-bottom: 15px;
  color: #00f2fe;
  font-size: 16px;
  font-weight: 600;
}

.composition-item {
  text-align: center;
  padding: 15px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.comp-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 8px;
}

.comp-value {
  font-size: 24px;
  font-weight: 600;
  color: #00f2fe;
}

.final-score {
  margin-top: 20px;
  text-align: center;
  padding: 15px;
  background: rgba(0, 242, 254, 0.1);
  border-radius: 4px;
  border: 1px solid rgba(0, 242, 254, 0.2);
}

.teacher-comment {
  margin-top: 25px;
}
</style>
