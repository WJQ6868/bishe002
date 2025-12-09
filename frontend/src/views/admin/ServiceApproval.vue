<template>
  <div class="service-approval">
    <div class="page-header">
      <h2>办事审批</h2>
      <div class="filters">
        <el-select v-model="statusFilter" placeholder="筛选状态" @change="fetchApplications" style="width: 150px">
          <el-option label="全部" value="" />
          <el-option label="待审核" value="pending" />
          <el-option label="办理中" value="processing" />
          <el-option label="已通过" value="approved" />
          <el-option label="已驳回" value="rejected" />
        </el-select>
      </div>
    </div>

    <el-table :data="applications" v-loading="loading" border style="width: 100%">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="expand-details">
            <div class="section">
              <h4>申请表单</h4>
              <el-descriptions :column="2" border>
                <el-descriptions-item
                  v-for="(value, key) in row.form_data"
                  :key="key"
                  :label="key"
                >
                  {{ value }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
            
            <div class="section" v-if="row.materials.length > 0">
              <h4>附件材料</h4>
              <div v-for="(mat, idx) in row.materials" :key="idx" class="material-item">
                <el-icon><Document /></el-icon>
                <span>{{ mat.name }}</span>
                <el-button type="primary" link size="small">查看</el-button>
              </div>
            </div>

            <div class="section">
              <h4>办理进度</h4>
              <el-timeline>
                <el-timeline-item
                  v-for="(node, index) in row.progress_nodes"
                  :key="index"
                  :timestamp="node.time"
                  :type="node.status === 'completed' ? 'success' : 'primary'"
                >
                  {{ node.node }} - {{ node.desc }}
                </el-timeline-item>
              </el-timeline>
            </div>
          </div>
        </template>
      </el-table-column>
      
      <el-table-column prop="id" label="申请ID" width="80" />
      <el-table-column prop="service_name" label="办事项目" width="150" />
      <el-table-column label="申请人" width="120">
        <template #default="{ row }">
          {{ row.applicant_id }} ({{ row.applicant_role === 'student' ? '学生' : '教师' }})
        </template>
      </el-table-column>
      <el-table-column prop="submit_time" label="提交时间" width="180">
        <template #default="{ row }">
          {{ formatTime(row.submit_time) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'pending'"
            type="success"
            size="small"
            @click="handleApprove(row, 'approved')"
          >
            通过
          </el-button>
          <el-button
            v-if="row.status === 'pending'"
            type="danger"
            size="small"
            @click="handleApprove(row, 'rejected')"
          >
            驳回
          </el-button>
          <el-button type="primary" size="small" link @click="viewDetail(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 审批弹窗 -->
    <el-dialog v-model="approvalVisible" :title="approvalType === 'approved' ? '审批通过' : '驳回申请'" width="500px">
      <el-form :model="approvalForm" label-width="80px">
        <el-form-item label="审批意见" required>
          <el-input
            v-model="approvalForm.opinion"
            type="textarea"
            :rows="4"
            :placeholder="approvalType === 'approved' ? '请输入审批意见（选填）' : '请输入驳回原因'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approvalVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitApproval">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document } from '@element-plus/icons-vue'

const loading = ref(true)
const applications = ref<any[]>([])
const statusFilter = ref('')
const approvalVisible = ref(false)
const approvalType = ref<'approved' | 'rejected'>('approved')
const currentApply = ref<any>(null)
const submitting = ref(false)
const approvalForm = ref({
  opinion: ''
})

const fetchApplications = async () => {
  loading.value = true
  try {
    const params = statusFilter.value ? { status: statusFilter.value } : {}
    const response = await axios.get('/api/service/admin/list', { params })
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
  return map[status] || status
}

const formatTime = (timeStr: string) => {
  if (!timeStr) return ''
  return new Date(timeStr).toLocaleString()
}

const handleApprove = (item: any, type: 'approved' | 'rejected') => {
  currentApply.value = item
  approvalType.value = type
  approvalForm.value.opinion = ''
  approvalVisible.value = true
}

const submitApproval = async () => {
  if (approvalType.value === 'rejected' && !approvalForm.value.opinion) {
    ElMessage.warning('驳回申请时必须填写原因')
    return
  }

  submitting.value = true
  try {
    await axios.put('/api/service/apply/approve', {
      id: currentApply.value.id,
      result: approvalType.value,
      opinion: approvalForm.value.opinion || '审批通过'
    })

    ElMessage.success('审批成功')
    approvalVisible.value = false
    fetchApplications()
  } catch (error) {
    console.error('审批失败', error)
    ElMessage.error('审批失败，请重试')
  } finally {
    submitting.value = false
  }
}

const viewDetail = (item: any) => {
  ElMessageBox.alert(
    `<div style="max-height: 400px; overflow-y: auto;">
      <h3>${item.service_name}</h3>
      <p><strong>申请人:</strong> ${item.applicant_id} (${item.applicant_role === 'student' ? '学生' : '教师'})</p>
      <p><strong>提交时间:</strong> ${formatTime(item.submit_time)}</p>
      <p><strong>状态:</strong> ${getStatusLabel(item.status)}</p>
      ${item.opinion ? `<p><strong>审批意见:</strong> ${item.opinion}</p>` : ''}
    </div>`,
    '申请详情',
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: '关闭'
    }
  )
}

onMounted(() => {
  fetchApplications()
})
</script>

<style scoped>
.service-approval {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.expand-details {
  padding: 20px;
  background: #f5f7fa;
}

.section {
  margin-bottom: 20px;
}

.section h4 {
  margin: 0 0 10px;
  color: #303133;
  border-left: 4px solid #409eff;
  padding-left: 10px;
}

.material-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  background: white;
  border-radius: 4px;
  margin-bottom: 5px;
}
</style>
