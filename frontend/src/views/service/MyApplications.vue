<template>
  <div class="my-applications">
    <div class="page-header">
      <h2>我的申请</h2>
      <el-button @click="$router.push('/service/hall')">返回办事大厅</el-button>
    </div>

    <div class="applications-list" v-loading="loading">
      <el-card v-for="item in applications" :key="item.id" class="apply-card">
        <template #header>
          <div class="card-header">
            <span class="service-name">{{ item.service_name }}</span>
            <el-tag :type="getStatusType(item.status)">{{ getStatusLabel(item.status) }}</el-tag>
          </div>
        </template>
        
        <div class="card-body">
          <div class="info-row">
            <span class="label">提交时间：</span>
            <span class="value">{{ formatTime(item.submit_time) }}</span>
          </div>
          
          <div class="progress-section">
            <el-steps :active="getActiveStep(item.progress_nodes)" finish-status="success" align-center>
              <el-step 
                v-for="(node, index) in item.progress_nodes" 
                :key="index" 
                :title="node.node" 
                :description="node.time ? node.time.split(' ')[0] : ''"
              />
            </el-steps>
          </div>

          <div class="action-footer">
            <el-button type="primary" link @click="viewDetail(item)">查看详情</el-button>
          </div>
        </div>
      </el-card>

      <el-empty v-if="!loading && applications.length === 0" description="暂无申请记录" />
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="申请详情" width="600px">
      <div v-if="currentApply" class="detail-content">
        <el-descriptions title="基本信息" :column="1" border>
          <el-descriptions-item label="办事项目">{{ currentApply.service_name }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ formatTime(currentApply.submit_time) }}</el-descriptions-item>
          <el-descriptions-item label="当前状态">
            <el-tag :type="getStatusType(currentApply.status)">{{ getStatusLabel(currentApply.status) }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div class="section-title">申请表单</div>
        <div class="form-data-view">
          <div v-for="(value, key) in currentApply.form_data" :key="key" class="data-item">
            <span class="key">{{ key }}：</span>
            <span class="value">{{ value }}</span>
          </div>
        </div>

        <div class="section-title">办理进度</div>
        <el-timeline>
          <el-timeline-item
            v-for="(node, index) in currentApply.progress_nodes"
            :key="index"
            :timestamp="node.time"
            :type="node.status === 'completed' ? 'success' : (node.status === 'rejected' ? 'danger' : 'primary')"
          >
            <h4>{{ node.node }}</h4>
            <p v-if="node.desc">{{ node.desc }}</p>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const loading = ref(true)
const applications = ref<any[]>([])
const detailVisible = ref(false)
const currentApply = ref<any>(null)

const fetchApplications = async () => {
  try {
    const response = await axios.get('/service/apply/list', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    applications.value = response.data
  } catch (error) {
    console.error('获取申请列表失败', error)
    ElMessage.error('获取申请列表失败')
  } finally {
    loading.value = false
  }
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'warning',
    processing: 'primary',
    approved: 'success',
    rejected: 'danger',
    completed: 'success'
  }
  return map[status] || 'info'
}

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: '待审核',
    processing: '办理中',
    approved: '已通过',
    rejected: '已驳回',
    completed: '已完成'
  }
  return map[status] || '未知状态'
}

const formatTime = (timeStr: string) => {
  if (!timeStr) return ''
  return new Date(timeStr).toLocaleString()
}

const getActiveStep = (nodes: any[]) => {
  return nodes.filter(n => n.status === 'completed').length
}

const viewDetail = (item: any) => {
  currentApply.value = item
  detailVisible.value = true
}

onMounted(() => {
  fetchApplications()
})
</script>

<style scoped>
.my-applications {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: var(--el-box-shadow-light);
  padding: 16px 18px;
  gap: 12px;
  flex-wrap: wrap;
}

.page-header h2 {
  margin: 0;
  color: var(--el-text-color-primary);
}

.apply-card {
  margin-bottom: 16px;
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  transition: box-shadow 0.25s ease, transform 0.25s ease;
}

.apply-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--el-box-shadow);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.service-name {
  font-weight: bold;
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.info-row {
  margin-bottom: 15px;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.progress-section {
  background: var(--el-fill-color-light);
  padding: 18px;
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  margin-bottom: 15px;
}

.action-footer {
  text-align: right;
}

.section-title {
  font-weight: bold;
  margin: 20px 0 10px;
  padding-left: 10px;
  border-left: 4px solid var(--el-color-primary);
  color: var(--el-text-color-primary);
}

.form-data-view {
  background: var(--el-fill-color-light);
  padding: 15px;
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
}

.data-item {
  margin-bottom: 8px;
  font-size: 14px;
}

.data-item .key {
  color: var(--el-text-color-secondary);
  margin-right: 10px;
}

.data-item .value {
  color: var(--el-text-color-primary);
}
</style>
