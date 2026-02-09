<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import 'echarts-gl'
import { Reading, User, DataLine, School } from '@element-plus/icons-vue'

type RangePreset = '7d' | '30d' | 'custom'
type UserAggMode = 'day' | 'week'
type AiFeature = 'course_assistant' | 'lesson_plan' | 'customer_service'
type AiResult = 'success' | 'failed'
type UserType = 'student' | 'teacher' | 'unknown'

interface AiUsageRecord {
  ts: string
  feature: AiFeature
  result: AiResult
  userType: UserType
}

const stats = ref({
  total_courses: 0,
  total_students: 0,
  total_teachers: 0,
  available_classrooms: 0
})

const userRole = ref(localStorage.getItem('user_role') || 'student')
const showUsageCharts = computed(() => userRole.value === 'admin')

const rangePreset = ref<RangePreset>('7d')
const customRange = ref<[Date, Date] | null>(null)
const userAggMode = ref<UserAggMode>('day')
const usageRecords = ref<AiUsageRecord[]>([])
const usageLoading = ref(false)
const usageError = ref('')
const lineEmpty = ref(false)
const threeDEmpty = ref(false)

const FEATURE_META: Record<AiFeature, { label: string; color: string; lineType: 'solid' | 'dashed' | 'dotted' }> = {
  course_assistant: { label: 'AI课程助手', color: '#00f2fe', lineType: 'solid' },
  lesson_plan: { label: '智能教案', color: '#67C23A', lineType: 'dashed' },
  customer_service: { label: 'AI客服', color: '#E6A23C', lineType: 'dotted' }
}

const featureKeys = Object.keys(FEATURE_META) as AiFeature[]
const featureLabelMap = Object.fromEntries(featureKeys.map((k) => [FEATURE_META[k].label, k]))

const MAX_RECORDS = 10000

let timer: any = null
let lineChart: echarts.ECharts | null = null
let usage3dChart: echarts.ECharts | null = null

const fetchStats = async () => {
  try {
    const res = await axios.get('/dashboard/stats')
    stats.value = res.data
  } catch (e) {
    ElMessage.error('统计数据获取失败')
  }
}

const loadUsageRecords = async () => {
  if (!showUsageCharts.value) {
    usageRecords.value = []
    usageLoading.value = false
    usageError.value = ''
    return
  }
  usageLoading.value = true
  usageError.value = ''
  try {
    const { start, end } = getRangeWindow()
    const res = await axios.get('/admin/ai/usage', {
      params: {
        start: start.toISOString(),
        end: end.toISOString(),
        limit: MAX_RECORDS
      }
    })
    const rawRecords = Array.isArray(res.data?.records) ? res.data.records : []
    const records = rawRecords
      .filter((item: any) => featureKeys.includes(item.feature))
      .map((item: any) => ({
        ts: item.ts,
        feature: item.feature,
        result: item.result === 'failed' ? 'failed' : 'success',
        userType: item.userType === 'teacher' || item.userType === 'student' ? item.userType : 'unknown'
      }))
    usageRecords.value = records
  } catch (e) {
    usageError.value = 'AI 调度数据加载失败'
    usageRecords.value = []
  } finally {
    usageLoading.value = false
  }
}

const getRangeWindow = () => {
  const end = new Date()
  if (rangePreset.value === 'custom' && customRange.value?.length === 2) {
    const [start, rangeEnd] = customRange.value
    return { start, end: rangeEnd }
  }
  if (rangePreset.value === '30d') {
    return { start: new Date(end.getTime() - 30 * 24 * 60 * 60 * 1000), end }
  }
  return { start: new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000), end }
}

const formatBucketKey = (date: Date, mode: 'hour' | 'day') => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  if (mode === 'hour') {
    const hour = String(date.getHours()).padStart(2, '0')
    return `${year}-${month}-${day} ${hour}:00`
  }
  return `${year}-${month}-${day}`
}

const bucketToTime = (bucket: string, mode: 'hour' | 'day') => {
  if (mode === 'hour') {
    return new Date(bucket.replace(' ', 'T') + ':00')
  }
  return new Date(bucket + 'T00:00:00')
}

const buildBuckets = (start: Date, end: Date, mode: 'hour' | 'day') => {
  const buckets: string[] = []
  const cursor = new Date(start.getTime())
  if (mode === 'day') {
    cursor.setHours(0, 0, 0, 0)
  } else {
    cursor.setMinutes(0, 0, 0)
  }
  while (cursor <= end) {
    buckets.push(formatBucketKey(cursor, mode))
    if (mode === 'hour') {
      cursor.setHours(cursor.getHours() + 1)
    } else {
      cursor.setDate(cursor.getDate() + 1)
    }
  }
  return buckets
}

const aggregateLineData = (records: AiUsageRecord[], start: Date, end: Date) => {
  const rangeDays = Math.max(1, Math.ceil((end.getTime() - start.getTime()) / (24 * 60 * 60 * 1000)))
  const mode: 'hour' | 'day' = rangeDays <= 2 ? 'hour' : 'day'
  const buckets = buildBuckets(start, end, mode)
  const statsByFeature: Record<AiFeature, Record<string, { total: number; success: number; failed: number }>> = {
    course_assistant: {},
    lesson_plan: {},
    customer_service: {}
  }
  const filtered = records.filter((r) => {
    const ts = new Date(r.ts).getTime()
    return ts >= start.getTime() && ts <= end.getTime()
  })
  filtered.forEach((record) => {
    const bucket = formatBucketKey(new Date(record.ts), mode)
    if (!statsByFeature[record.feature][bucket]) {
      statsByFeature[record.feature][bucket] = { total: 0, success: 0, failed: 0 }
    }
    const stat = statsByFeature[record.feature][bucket]
    stat.total += 1
    stat[record.result] += 1
  })
  return { buckets, statsByFeature, mode, totalCount: filtered.length }
}

const aggregate3dData = (records: AiUsageRecord[], start: Date, end: Date, mode: UserAggMode) => {
  const buckets: string[] = []
  const cursor = new Date(start.getTime())
  cursor.setHours(0, 0, 0, 0)
  const step = mode === 'week' ? 7 : 1
  while (cursor <= end) {
    buckets.push(formatBucketKey(cursor, 'day'))
    cursor.setDate(cursor.getDate() + step)
  }
  const userTypes: UserType[] = ['student', 'teacher']
  const counts: Record<string, Record<UserType, number>> = {}
  let totalCount = 0
  records.forEach((record) => {
    const ts = new Date(record.ts).getTime()
    if (ts < start.getTime() || ts > end.getTime()) return
    if (record.userType !== 'student' && record.userType !== 'teacher') return
    totalCount += 1
    const dayKey = formatBucketKey(new Date(record.ts), 'day')
    const bucketIndex = buckets.findIndex((b) => b <= dayKey && dayKey < addDaysKey(b, step))
    if (bucketIndex === -1) return
    const bucketKey = buckets[bucketIndex]
    if (!counts[bucketKey]) {
      counts[bucketKey] = { student: 0, teacher: 0 }
    }
    counts[bucketKey][record.userType] += 1
  })
  const data: Array<[number, number, number]> = []
  buckets.forEach((bucket, x) => {
    userTypes.forEach((userType, y) => {
      data.push([x, y, counts[bucket]?.[userType] || 0])
    })
  })
  return { buckets, userTypes, data, totalCount }
}

const addDaysKey = (bucket: string, step: number) => {
  const date = new Date(bucket + 'T00:00:00')
  date.setDate(date.getDate() + step)
  return formatBucketKey(date, 'day')
}

const initCharts = () => {
  if (!showUsageCharts.value) return
  const lineDom = document.getElementById('activity-chart')
  const usageDom = document.getElementById('usage-3d-chart')

  if (lineDom) {
    lineChart = echarts.init(lineDom)
  }
  if (usageDom) {
    usage3dChart = echarts.init(usageDom)
  }
}

const updateLineChart = () => {
  if (!lineChart) return
  if (usageError.value) {
    lineChart.clear()
    lineEmpty.value = false
    return
  }
  const { start, end } = getRangeWindow()
  const { buckets, statsByFeature, mode, totalCount } = aggregateLineData(usageRecords.value, start, end)
  lineEmpty.value = totalCount === 0

  const series = featureKeys.map((feature) => {
    const meta = FEATURE_META[feature]
    const data = buckets.map((bucket) => {
      const stat = statsByFeature[feature][bucket]
      return [bucketToTime(bucket, mode).getTime(), stat ? stat.total : 0]
    })
    return {
      name: meta.label,
      type: 'line',
      smooth: true,
      showSymbol: false,
      sampling: 'lttb',
      lineStyle: { color: meta.color, type: meta.lineType, width: 2 },
      itemStyle: { color: meta.color },
      emphasis: { focus: 'series' },
      data
    }
  })

  const tooltipFormatter = (params: any) => {
    if (!Array.isArray(params)) return ''
    const timeLabel = params[0]?.axisValueLabel || ''
    const lines = params.map((item: any) => {
      const feature = featureLabelMap[item.seriesName]
      const bucketKey = mode === 'hour'
        ? formatBucketKey(new Date(item.value[0]), 'hour')
        : formatBucketKey(new Date(item.value[0]), 'day')
      const stat = feature ? statsByFeature[feature][bucketKey] : null
      const success = stat?.success ?? 0
      const failed = stat?.failed ?? 0
      return `${item.marker}${item.seriesName}：${item.value[1]} 次 (成功 ${success}/失败 ${failed})`
    })
    return [timeLabel, ...lines].join('<br/>')
  }

  lineChart.setOption({
    backgroundColor: 'transparent',
    legend: {
      top: 6,
      right: 0,
      textStyle: { color: 'rgba(255,255,255,0.7)' }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line' },
      backgroundColor: 'rgba(20, 20, 20, 0.9)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: { color: '#fff' },
      formatter: tooltipFormatter
    },
    grid: { top: 50, left: '3%', right: '4%', bottom: 40, containLabel: true },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.3)' } },
      axisLabel: {
        color: 'rgba(255,255,255,0.7)',
        formatter: (value: number) => {
          const d = new Date(value)
          return mode === 'hour' ? `${String(d.getHours()).padStart(2, '0')}:00` : `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '调用次数',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.7)' }
    },
    dataZoom: [
      { type: 'inside', throttle: 50 },
      { type: 'slider', height: 16, bottom: 8, borderColor: 'rgba(255,255,255,0.15)', textStyle: { color: '#ccc' } }
    ],
    series
  })
}

const update3dChart = () => {
  if (!usage3dChart) return
  if (usageError.value) {
    usage3dChart.clear()
    threeDEmpty.value = false
    return
  }
  const { start, end } = getRangeWindow()
  const { buckets, userTypes, data, totalCount } = aggregate3dData(usageRecords.value, start, end, userAggMode.value)
  threeDEmpty.value = totalCount === 0

  usage3dChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (params: any) => {
        const [xIndex, yIndex, value] = params.value
        const userLabel = userTypes[yIndex] === 'student' ? '学生' : '教师'
        return `${buckets[xIndex]}<br/>${userLabel}：${value} 次`
      }
    },
    grid3D: {
      boxWidth: 140,
      boxDepth: 50,
      viewControl: {
        projection: 'perspective',
        rotateSensitivity: 1.2,
        zoomSensitivity: 1.2,
        panSensitivity: 1
      },
      light: {
        main: { intensity: 1.1, shadow: true },
        ambient: { intensity: 0.4 }
      }
    },
    xAxis3D: {
      type: 'category',
      data: buckets,
      axisLabel: { color: 'rgba(255,255,255,0.7)' },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.25)' } }
    },
    yAxis3D: {
      type: 'category',
      data: userTypes.map((t) => (t === 'student' ? '学生' : '教师')),
      axisLabel: { color: 'rgba(255,255,255,0.7)' },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.25)' } }
    },
    zAxis3D: {
      type: 'value',
      name: '使用次数',
      axisLabel: { color: 'rgba(255,255,255,0.7)' },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.25)' } }
    },
    visualMap: {
      max: Math.max(10, ...data.map((item) => item[2])),
      inRange: {
        color: ['#144a74', '#00f2fe', '#67C23A']
      },
      textStyle: { color: '#ccc' }
    },
    series: [
      {
        type: 'bar3D',
        data,
        shading: 'lambert',
        bevelSize: 0.2,
        itemStyle: { opacity: 0.9 }
      }
    ]
  })
}

const updateCharts = () => {
  if (!showUsageCharts.value) return
  updateLineChart()
  update3dChart()
}

const handleRefresh = async () => {
  await fetchStats()
  if (showUsageCharts.value) {
    await loadUsageRecords()
    updateCharts()
  }
  ElMessage.success('已刷新')
}

const resizeCharts = () => {
  lineChart?.resize()
  usage3dChart?.resize()
}

watch([rangePreset, customRange], async () => {
  if (!showUsageCharts.value) return
  await loadUsageRecords()
  updateCharts()
})

watch(userAggMode, () => {
  if (!showUsageCharts.value) return
  updateCharts()
})

onMounted(async () => {
  initCharts()
  await fetchStats()
  if (showUsageCharts.value) {
    await loadUsageRecords()
    updateCharts()
  }
  timer = setInterval(async () => {
    await fetchStats()
    if (showUsageCharts.value) {
      await loadUsageRecords()
      updateCharts()
    }
  }, 60000)
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  window.removeEventListener('resize', resizeCharts)
  lineChart?.dispose()
  usage3dChart?.dispose()
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

    <div v-if="showUsageCharts" class="charts-row">
      <div class="tech-card chart-card wide">
        <div class="card-header">
          <div>
            <h3>AI使用频率趋势</h3>
            <p class="chart-sub">AI课程助手 / 智能教案 / AI客服</p>
          </div>
          <div class="chart-controls">
            <el-select v-model="rangePreset" size="small" class="control-item">
              <el-option label="最近7天" value="7d" />
              <el-option label="最近30天" value="30d" />
              <el-option label="自定义" value="custom" />
            </el-select>
            <el-date-picker
              v-if="rangePreset === 'custom'"
              v-model="customRange"
              type="daterange"
              unlink-panels
              size="small"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              class="control-item range-picker"
            />
          </div>
        </div>
        <div class="chart-body">
          <div id="activity-chart" class="chart-container"></div>
          <div v-if="usageLoading" class="chart-overlay">正在加载数据…</div>
          <div v-else-if="usageError" class="chart-overlay error">{{ usageError }}</div>
          <div v-else-if="lineEmpty" class="chart-overlay">暂无调度记录</div>
        </div>
      </div>
      
      <div class="tech-card chart-card narrow">
        <div class="card-header">
          <div>
            <h3>教师/学生使用对比</h3>
            <p class="chart-sub">范围与上方同步</p>
          </div>
          <div class="chart-controls">
            <el-select v-model="userAggMode" size="small" class="control-item">
              <el-option label="按日聚合" value="day" />
              <el-option label="按周聚合" value="week" />
            </el-select>
          </div>
        </div>
        <div class="chart-body">
          <div id="usage-3d-chart" class="chart-container"></div>
          <div v-if="usageLoading" class="chart-overlay">正在加载数据…</div>
          <div v-else-if="usageError" class="chart-overlay error">{{ usageError }}</div>
          <div v-else-if="threeDEmpty" class="chart-overlay">暂无对比数据</div>
        </div>
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
  height: 420px;
}

.chart-card { display: flex; flex-direction: column; gap: 16px; }
.wide { flex: 2; }
.narrow { flex: 1; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  color: #fff;
  border-left: 4px solid #00f2fe;
  padding-left: 12px;
}

.chart-sub {
  margin: 6px 0 0 16px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.chart-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.control-item {
  min-width: 120px;
}

.range-picker {
  min-width: 240px;
}

.chart-body {
  position: relative;
  flex: 1;
  min-height: 0;
}

.chart-container {
  width: 100%;
  height: 100%;
  min-height: 260px;
}

.chart-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  background: rgba(8, 16, 24, 0.65);
  border-radius: 10px;
  text-align: center;
  padding: 16px;
}

.chart-overlay.error {
  color: #f56c6c;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .charts-row {
    flex-direction: column;
    height: auto;
  }

  .chart-card {
    min-height: 340px;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .welcome-banner {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}
</style>
