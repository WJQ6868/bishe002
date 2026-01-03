<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Monitor, User, Lock, Connection, 
  Odometer, Files, DataAnalysis, School,
  CopyDocument, ArrowLeft
} from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// --- 1. 类型定义 ---
interface FunctionDemand {
  module: string
  desc: string
  icon: any
  color: string
  subFunctions: { label: string; children?: { label: string }[] }[]
}

interface UserDemand {
  role: string
  demand: string
  scene: string
}

interface NonFunctionDemand {
  type: string
  desc: string
  index: string
  icon: any
  percentage: number
  color: string
  detail: string // 需求依据
}

// --- 2. 状态管理 ---
const activeTab = ref('functional')
const loading = ref(true)
const selectedRole = ref('all')

// --- 3. 模拟数据 ---

// 功能需求数据
const functionDemands: FunctionDemand[] = [
  {
    module: '教学资源管理',
    desc: '实现教室、实验室、设备的数字化管理与状态监控',
    icon: School,
    color: '#409EFF',
    subFunctions: [
      { label: '资源信息维护', children: [{ label: '新增/编辑资源' }, { label: '批量导入导出' }] },
      { label: '状态监控', children: [{ label: '实时状态查看' }, { label: '利用率统计' }] },
      { label: '预约管理', children: [{ label: '预约审核' }, { label: '冲突检测' }] }
    ]
  },
  {
    module: '课程管理',
    desc: '全生命周期的课程信息维护与选课控制',
    icon: Files,
    color: '#67C23A',
    subFunctions: [
      { label: '课程库管理', children: [{ label: '必修/选修分类' }, { label: '学分设置' }] },
      { label: '选课控制', children: [{ label: '容量限制' }, { label: '选课时间控制' }] },
      { label: '课程评估', children: [{ label: '满意度调查' }, { label: '评估报表' }] }
    ]
  },
  {
    module: '学生管理',
    desc: '学生学籍、成绩、个人成长的全方位记录',
    icon: User,
    color: '#E6A23C',
    subFunctions: [
      { label: '学籍管理', children: [{ label: '基本信息' }, { label: '班级分配' }] },
      { label: '成绩管理', children: [{ label: '成绩录入' }, { label: 'GPA计算' }] },
      { label: '个人成长', children: [{ label: '画像分析' }, { label: '预警通知' }] }
    ]
  },
  {
    module: '考试管理',
    desc: '智能化的考试安排与监考分配',
    icon: Monitor,
    color: '#F56C6C',
    subFunctions: [
      { label: '排考管理', children: [{ label: '考场分配' }, { label: '时间冲突检测' }] },
      { label: '监考安排', children: [{ label: '教师排班' }, { label: '监考通知' }] },
      { label: '成绩分析', children: [{ label: '正态分布分析' }, { label: '试卷质量分析' }] }
    ]
  },
  {
    module: '数据分析与决策',
    desc: '基于大数据的教学质量监控与辅助决策',
    icon: DataAnalysis,
    color: '#909399',
    subFunctions: [
      { label: '学情分析', children: [{ label: '挂科预警' }, { label: '学习趋势' }] },
      { label: '资源报表', children: [{ label: '利用率分析' }, { label: '维修统计' }] },
      { label: '教学质量', children: [{ label: '评教分析' }, { label: '教师绩效' }] }
    ]
  }
]

// 用户需求数据
const userDemandsRaw: UserDemand[] = [
  { role: 'student', demand: '查询个人课表与成绩', scene: '学期初查看课表，期末查询成绩及GPA' },
  { role: 'student', demand: '在线选课与退课', scene: '选课开放期间进行抢课，或在规定时间内退课' },
  { role: 'student', demand: '申请教室/实验室预约', scene: '社团活动或自习需要使用空闲教室' },
  { role: 'student', demand: '查看学业预警通知', scene: '成绩下滑或缺勤过多时接收系统提醒' },
  { role: 'teacher', demand: '录入与修改学生成绩', scene: '期末考试结束后批量录入班级成绩' },
  { role: 'teacher', demand: '查看授课课表与教室', scene: '每周查看教学安排，确认上课地点' },
  { role: 'teacher', demand: '生成智能教案', scene: '备课时利用AI辅助生成课程大纲与教案' },
  { role: 'teacher', demand: '申请调课/代课', scene: '因公出差或生病时申请调整上课时间' },
  { role: 'admin', demand: '维护基础数据（师生/课程）', scene: '每学年导入新生数据，更新课程库' },
  { role: 'admin', demand: '进行智能排课', scene: '学期初利用算法自动生成全校课表' },
  { role: 'admin', demand: '监控教学资源状态', scene: '实时查看教室使用情况，处理报修申请' },
  { role: 'admin', demand: '查看全校教学统计报表', scene: '期末总结时导出教学质量分析报告' }
]

// 非功能需求数据
const nonFunctionDemands: NonFunctionDemand[] = [
  { 
    type: '性能需求', 
    desc: '系统响应速度与并发处理能力', 
    index: '并发用户≥100，响应时间≤2s', 
    icon: Odometer, 
    percentage: 90, 
    color: '#409EFF',
    detail: '基于FastAPI异步处理与Redis缓存，确保高并发下系统流畅'
  },
  { 
    type: '安全性', 
    desc: '数据隐私保护与访问控制', 
    index: 'JWT认证，敏感数据加密存储', 
    icon: Lock, 
    percentage: 100, 
    color: '#67C23A',
    detail: '采用RBAC权限模型，密码Hash存储，防止SQL注入与XSS攻击'
  },
  { 
    type: '可扩展性', 
    desc: '系统架构的灵活性与扩展能力', 
    index: '模块化设计，支持微服务扩展', 
    icon: Connection, 
    percentage: 85, 
    color: '#E6A23C',
    detail: '前后端分离架构，适配未来新增教学模块（如在线考试）'
  },
  { 
    type: '易用性', 
    desc: '用户界面友好度与操作便捷性', 
    index: '3步内完成核心操作，响应式布局', 
    icon: User, 
    percentage: 95, 
    color: '#F56C6C',
    detail: 'Element Plus组件库统一UI规范，提供清晰的导航与提示'
  }
]

// --- 4. 核心逻辑 ---

// 骨架屏模拟
onMounted(() => {
  setTimeout(() => {
    loading.value = false
  }, 1000)
})

// 用户需求筛选
const filteredUserDemands = computed(() => {
  if (selectedRole.value === 'all') return userDemandsRaw
  return userDemandsRaw.filter(d => d.role === selectedRole.value)
})

// 角色名称映射
const getRoleName = (role: string) => {
  const map: Record<string, string> = {
    student: '学生',
    teacher: '教师',
    admin: '管理员'
  }
  return map[role] || role
}

// 复制文本
const copyText = (text: string) => {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制需求描述')
  })
}

const goBack = () => {
  router.push('/dashboard')
}

</script>

<template>
  <div class="requirements-page">
    <!-- 顶部 Header -->
    <div class="page-header">
      <div class="header-content">
        <el-button link class="back-btn" @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回首页
        </el-button>
        <h1>智能教务系统需求分析</h1>
        <p class="subtitle">基于高校教务管理实际需求，确保系统实用性与适用性</p>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-container">
      <el-skeleton :rows="10" animated v-if="loading" />
      
      <el-tabs v-else v-model="activeTab" class="demand-tabs" type="border-card">
        
        <!-- 功能需求 -->
        <el-tab-pane label="功能需求" name="functional">
          <div class="functional-grid">
            <el-card 
              v-for="item in functionDemands" 
              :key="item.module" 
              class="func-card" 
              shadow="hover"
              :style="{ borderTop: `3px solid ${item.color}` }"
            >
              <div class="card-header">
                <el-icon :size="24" :color="item.color"><component :is="item.icon" /></el-icon>
                <h3>{{ item.module }}</h3>
              </div>
              <div class="card-desc" @click="copyText(item.desc)" title="点击复制">
                {{ item.desc }} <el-icon class="copy-icon"><CopyDocument /></el-icon>
              </div>
              <el-divider style="margin: 15px 0" />
              <div class="sub-funcs">
                <el-tree 
                  :data="item.subFunctions" 
                  :props="{ label: 'label', children: 'children' }"
                  default-expand-all
                />
              </div>
            </el-card>
          </div>
        </el-tab-pane>

        <!-- 用户需求 -->
        <el-tab-pane label="用户需求" name="user">
          <div class="filter-bar">
            <span>角色筛选：</span>
            <el-radio-group v-model="selectedRole" size="small">
              <el-radio-button label="all">全部</el-radio-button>
              <el-radio-button label="student">学生</el-radio-button>
              <el-radio-button label="teacher">教师</el-radio-button>
              <el-radio-button label="admin">管理员</el-radio-button>
            </el-radio-group>
          </div>
          <el-table :data="filteredUserDemands" style="width: 100%" stripe>
            <el-table-column prop="role" label="用户角色" width="120">
              <template #default="{ row }">
                <el-tag :type="row.role === 'admin' ? 'danger' : row.role === 'teacher' ? 'warning' : 'success'">
                  {{ getRoleName(row.role) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="demand" label="核心需求" min-width="200" />
            <el-table-column prop="scene" label="使用场景" min-width="300" />
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="expand-content">
                  <p><strong>详细说明：</strong>该需求旨在满足{{ getRoleName(row.role) }}在{{ row.scene }}中的操作需要，是系统核心流程的重要组成部分。</p>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 非功能需求 -->
        <el-tab-pane label="非功能需求" name="non-functional">
          <div class="non-func-list">
            <el-card 
              v-for="item in nonFunctionDemands" 
              :key="item.type" 
              class="non-func-card" 
              shadow="hover"
            >
              <div class="nf-content">
                <div class="nf-icon" :style="{ background: item.color }">
                  <el-icon color="#fff" :size="24"><component :is="item.icon" /></el-icon>
                </div>
                <div class="nf-info">
                  <h3>{{ item.type }}</h3>
                  <p class="desc">{{ item.desc }}</p>
                  <p class="index"><strong>指标：</strong>{{ item.index }}</p>
                  <div class="progress-bar">
                    <span>达成度：</span>
                    <el-progress :percentage="item.percentage" :color="item.color" style="width: 200px" />
                  </div>
                </div>
              </div>
              <div class="nf-detail">
                <el-alert :title="item.detail" type="info" :closable="false" show-icon />
              </div>
            </el-card>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 底部总结 -->
      <div class="page-footer">
        <el-alert 
          title="需求分析总结" 
          type="success" 
          description="基于高校教务实际调研，覆盖管理、教学、学习全场景，为技术选型（Vue3+FastAPI）与系统设计提供依据，确保功能贴合实际。"
          :closable="false"
          center
          show-icon
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.requirements-page {
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

.demand-tabs {
  background: var(--card-bg);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-color);
  min-height: 500px;
}

/* 功能需求 */
.functional-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  padding: 10px;
}
.func-card {
  transition: transform 0.3s;
}
.func-card:hover {
  transform: translateY(-5px);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.card-header h3 {
  margin: 0;
  font-size: 18px;
}
.card-desc {
  font-size: 13px;
  color: var(--el-text-color-regular);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
}
.card-desc:hover {
  color: #409EFF;
}
.copy-icon {
  display: none;
}
.card-desc:hover .copy-icon {
  display: inline-block;
}
.sub-funcs {
  max-height: 200px;
  overflow-y: auto;
}

/* 用户需求 */
.filter-bar {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.expand-content {
  padding: 10px 20px;
  background: rgba(230, 162, 60, 0.1);
  color: #e6a23c;
  border-radius: 4px;
}
/* 表格hover高亮 */
:deep(.el-table__body tr:hover > td) {
  background-color: rgba(64, 158, 255, 0.1) !important;
}

/* 非功能需求 */
.non-func-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 10px;
}
.non-func-card {
  border-left: 5px solid transparent;
}
.non-func-card:hover {
  border-left-color: inherit; /* 需要JS动态设置，这里简化 */
}
.nf-content {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 15px;
}
.nf-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}
.nf-info {
  flex: 1;
}
.nf-info h3 {
  margin: 0 0 5px;
  font-size: 18px;
}
.nf-info .desc {
  color: #909399;
  margin: 0 0 10px;
}
.nf-info .index {
  color: #303133;
  margin: 0 0 10px;
}
.progress-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #606266;
}

.page-footer {
  margin-top: auto;
  padding-bottom: 20px;
}
</style>
