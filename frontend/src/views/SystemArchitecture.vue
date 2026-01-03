<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Download, Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const router = useRouter()

// --- 1. 状态管理 ---
const activeTab = ref('overall')
const loading = ref(true)
const chartRef = ref<HTMLElement | null>(null)
let myChart: echarts.ECharts | null = null

// 流程切换
const activeFlow = ref('course_selection')
const flowOptions = [
  { label: '学生选课流程', value: 'course_selection' },
  { label: '教师成绩录入', value: 'grade_entry' },
  { label: '资源预约流程', value: 'resource_reservation' }
]

// --- 2. 图表配置 ---

// 整体架构图配置
const getOverallOption = () => ({
  tooltip: {
    trigger: 'item',
    formatter: '{b}: {c}'
  },
  series: [
    {
      type: 'graph',
      layout: 'none',
      symbolSize: [200, 60],
      symbol: 'rect',
      label: { show: true, fontSize: 14, color: '#fff' },
      itemStyle: { borderRadius: 4 },
      data: [
        { name: '前端展示层\n(Vue3 + Element Plus)', x: 300, y: 100, itemStyle: { color: '#409EFF' }, value: '用户交互界面，响应式设计' },
        { name: 'API 网关层\n(FastAPI Router)', x: 300, y: 250, itemStyle: { color: '#67C23A' }, value: '请求路由分发，权限校验' },
        { name: '业务服务层\n(Service Logic)', x: 300, y: 400, itemStyle: { color: '#E6A23C' }, value: '核心业务逻辑处理' },
        { name: '数据存储层\n(MySQL + Redis)', x: 300, y: 550, itemStyle: { color: '#F56C6C' }, value: '持久化存储与缓存' }
      ],
      edges: [
        { source: 0, target: 1, symbol: ['none', 'arrow'] },
        { source: 1, target: 2, symbol: ['none', 'arrow'] },
        { source: 2, target: 3, symbol: ['none', 'arrow'] }
      ],
      lineStyle: { width: 2, curveness: 0 }
    }
  ]
})

// 模块架构图配置
const getModuleOption = () => ({
  tooltip: { trigger: 'item', triggerOn: 'mousemove' },
  series: [
    {
      type: 'tree',
      data: [{
        name: '智能教务系统',
        children: [
          {
            name: '教学资源管理',
            children: [{ name: '教室管理' }, { name: '实验室管理' }, { name: '设备管理' }, { name: '预约审核' }]
          },
          {
            name: '课程管理',
            children: [{ name: '课程库维护' }, { name: '选课控制' }, { name: '课程评估' }]
          },
          {
            name: '学生管理',
            children: [{ name: '学籍信息' }, { name: '成绩查询' }, { name: '个人成长' }]
          },
          {
            name: '考试管理',
            children: [{ name: '智能排考' }, { name: '监考安排' }, { name: '成绩分析' }]
          },
          {
            name: '数据分析',
            children: [{ name: '学情预警' }, { name: '资源利用率' }, { name: '教学质量' }]
          }
        ]
      }],
      top: '5%',
      left: '10%',
      bottom: '5%',
      right: '20%',
      symbolSize: 10,
      label: { position: 'left', verticalAlign: 'middle', align: 'right', fontSize: 14 },
      leaves: {
        label: { position: 'right', verticalAlign: 'middle', align: 'left' }
      },
      expandAndCollapse: true,
      animationDuration: 550,
      animationDurationUpdate: 750
    }
  ]
})

// 数据流程图配置
const getFlowOption = (flowType: string) => {
  let data: any[] = []
  let links: any[] = []
  
  if (flowType === 'course_selection') {
    data = [
      { name: '学生登录', x: 100, y: 300, itemStyle: { color: '#409EFF' } },
      { name: '浏览课程', x: 300, y: 300, itemStyle: { color: '#409EFF' } },
      { name: '加入志愿', x: 500, y: 300, itemStyle: { color: '#409EFF' } },
      { name: '系统校验\n(容量/冲突)', x: 500, y: 150, itemStyle: { color: '#E6A23C' } },
      { name: '提交结果', x: 700, y: 300, itemStyle: { color: '#67C23A' } }
    ]
    links = [
      { source: '学生登录', target: '浏览课程' },
      { source: '浏览课程', target: '加入志愿' },
      { source: '加入志愿', target: '系统校验\n(容量/冲突)' },
      { source: '系统校验\n(容量/冲突)', target: '加入志愿', label: { show: true, formatter: '失败' }, lineStyle: { curveness: 0.2 } },
      { source: '系统校验\n(容量/冲突)', target: '提交结果', label: { show: true, formatter: '通过' } }
    ]
  } else if (flowType === 'grade_entry') {
    data = [
      { name: '教师登录', x: 100, y: 300, itemStyle: { color: '#67C23A' } },
      { name: '选择课程', x: 300, y: 300, itemStyle: { color: '#67C23A' } },
      { name: '录入成绩', x: 500, y: 300, itemStyle: { color: '#67C23A' } },
      { name: '计算GPA', x: 500, y: 150, itemStyle: { color: '#E6A23C' } },
      { name: '发布成绩', x: 700, y: 300, itemStyle: { color: '#F56C6C' } }
    ]
    links = [
      { source: '教师登录', target: '选择课程' },
      { source: '选择课程', target: '录入成绩' },
      { source: '录入成绩', target: '计算GPA' },
      { source: '计算GPA', target: '录入成绩' },
      { source: '录入成绩', target: '发布成绩' }
    ]
  } else {
    data = [
      { name: '查询资源', x: 100, y: 300, itemStyle: { color: '#409EFF' } },
      { name: '提交预约', x: 300, y: 300, itemStyle: { color: '#409EFF' } },
      { name: '管理员审核', x: 500, y: 300, itemStyle: { color: '#E6A23C' } },
      { name: '审核通过', x: 700, y: 200, itemStyle: { color: '#67C23A' } },
      { name: '审核拒绝', x: 700, y: 400, itemStyle: { color: '#F56C6C' } }
    ]
    links = [
      { source: '查询资源', target: '提交预约' },
      { source: '提交预约', target: '管理员审核' },
      { source: '管理员审核', target: '审核通过' },
      { source: '管理员审核', target: '审核拒绝' }
    ]
  }

  return {
    tooltip: {},
    series: [{
      type: 'graph',
      layout: 'none',
      symbolSize: 80,
      symbol: 'rect',
      label: { show: true, color: '#fff' },
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: [4, 10],
      data: data.map(item => ({ ...item, symbolSize: [120, 50], itemStyle: { ...item.itemStyle, borderRadius: 4 } })),
      links: links,
      lineStyle: { width: 2, curveness: 0 }
    }]
  }
}

// --- 3. 核心逻辑 ---

const initChart = () => {
  if (!chartRef.value) return
  
  if (myChart) {
    myChart.dispose()
  }
  
  myChart = echarts.init(chartRef.value)
  
  let option = {}
  if (activeTab.value === 'overall') {
    option = getOverallOption()
  } else if (activeTab.value === 'module') {
    option = getModuleOption()
  } else {
    option = getFlowOption(activeFlow.value)
  }
  
  myChart.setOption(option)
  
  // 响应式调整
  window.addEventListener('resize', () => myChart?.resize())
}

// 监听 Tab 切换
watch(activeTab, () => {
  nextTick(() => initChart())
})

// 监听流程切换
watch(activeFlow, () => {
  if (activeTab.value === 'flow') {
    initChart()
  }
})

onMounted(() => {
  setTimeout(() => {
    loading.value = false
    nextTick(() => initChart())
  }, 800)
})

const goBack = () => router.push('/dashboard')

const downloadChart = () => {
  if (!myChart) return
  const url = myChart.getDataURL({
    type: 'png',
    pixelRatio: 2,
    backgroundColor: '#050505'
  })
  const a = document.createElement('a')
  a.download = 'architecture-diagram.png'
  a.href = url
  a.click()
}

</script>

<template>
  <div class="architecture-page">
    <!-- 顶部 Header -->
    <div class="page-header">
      <div class="header-content">
        <el-button link class="back-btn" @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回首页
        </el-button>
        <h1>智能教务系统架构设计</h1>
        <p class="subtitle">设计原则：明确功能模块、优化用户体验、确保系统稳定性</p>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-container">
      <el-skeleton :rows="15" animated v-if="loading" />
      
      <el-tabs v-else v-model="activeTab" class="arch-tabs" type="border-card">
        <el-tab-pane label="整体架构" name="overall" />
        <el-tab-pane label="模块架构" name="module" />
        <el-tab-pane label="数据流程" name="flow" />
        
        <div class="chart-container">
          <!-- 工具栏 -->
          <div class="chart-toolbar">
            <div v-if="activeTab === 'flow'" class="flow-selector">
              <span>核心流程：</span>
              <el-select v-model="activeFlow" size="small" style="width: 160px">
                <el-option v-for="opt in flowOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
            </div>
            <div class="right-tools">
              <el-button size="small" :icon="Refresh" @click="initChart">刷新</el-button>
              <el-button size="small" type="primary" :icon="Download" @click="downloadChart">导出图片</el-button>
            </div>
          </div>
          
          <!-- 图表区域 -->
          <div ref="chartRef" class="echarts-box"></div>
        </div>
      </el-tabs>

      <!-- 底部总结 -->
      <div class="page-footer">
        <el-alert 
          title="架构设计总结" 
          type="success" 
          description="架构设计遵循开发要点，明确功能模块与数据流程，采用模块化设计与分层架构，兼顾功能完整性与系统可扩展性，为开发与测试提供清晰依据。"
          :closable="false"
          center
          show-icon
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.architecture-page {
  min-height: 100vh;
  background-color: transparent;
  display: flex;
  flex-direction: column;
}

.page-header {
  background: var(--card-bg);
  backdrop-filter: blur(10px);
  padding: 20px 40px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border-bottom: 1px solid var(--border-color);
  text-align: center;
  position: relative;
}
.header-content {
  max-width: 1200px;
  margin: 0 auto;
  position: relative;
}
.back-btn {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  font-size: 16px;
}
.page-header h1 {
  margin: 0;
  font-size: 28px;
  color: var(--el-text-color-primary);
}
.subtitle {
  margin: 10px 0 0;
  color: #909399;
  font-size: 14px;
}

.main-container {
  flex: 1;
  max-width: 1200px;
  width: 100%;
  margin: 20px auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.arch-tabs {
  background: var(--card-bg);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-color);
  min-height: 600px;
  display: flex;
  flex-direction: column;
}
:deep(.el-tabs__content) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chart-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 10px;
}

.chart-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.echarts-box {
  flex: 1;
  min-height: 500px;
  width: 100%;
}

.page-footer {
  margin-top: auto;
  padding-bottom: 20px;
}
</style>
