<script setup lang="ts">
/**
 * 教师请假审批页面
 * 包含：待审批/已审批列表、审批弹窗、批量操作
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Close, Search, Download } from '@element-plus/icons-vue'
import axios from 'axios'

// --- 类型定义 ---
interface LeaveRecord {
  id: number
  student_id: number
  student_name: string
  course_id: number
  course_name: string
  type: string
  start_time: string
  end_time: string
  reason: string
  file_url?: string
  status: 'pending' | 'approved' | 'rejected' | 'recalled'
  opinion?: string
  create_time: string
}

// --- 状态管理 ---
const activeTab = ref('pending')
const leaves = ref<LeaveRecord[]>([])
const loading = ref(false)
const searchKeyword = ref('')
const filterType = ref('')

// 审批弹窗
const dialogVisible = ref(false)
const currentLeave = ref<LeaveRecord | null>(null)
const approveForm = reactive({
  result: 'approved',
  opinion: ''
})
const approving = ref(false)

// 批量操作
const selectedLeaves = ref<LeaveRecord[]>([])

// --- 初始化 ---
onMounted(() => {
  loadLeaves()
})

// 加载请假列表
const loadLeaves = async () => {
  loading.value = true
  try {
    const res = await axios.get('http://localhost:8000/api/leave/teacher/list', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    leaves.value = res.data
  } catch (error) {
    console.error('Failed to load leaves', error)
    ElMessage.error('无法加载请假列表')
  } finally {
    loading.value = false
  }
}

// 过滤列表
const filteredLeaves = computed(() => {
  let result = leaves.value
  
  // Tab 过滤
  if (activeTab.value === 'pending') {
    result = result.filter(l => l.status === 'pending')
  } else if (activeTab.value === 'processed') {
    result = result.filter(l => ['approved', 'rejected'].includes(l.status))
  }
  
  // 关键词过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(l => 
      l.student_name.includes(keyword) || 
      l.course_name.includes(keyword)
    )
  }
  
  // 类型过滤
  if (filterType.value) {
    result = result.filter(l => l.type === filterType.value)
  }
  
  return result
})

// 打开审批弹窗
const openApproveDialog = (leave: LeaveRecord) => {
  currentLeave.value = leave
  approveForm.result = 'approved'
  approveForm.opinion = ''
  dialogVisible.value = true
}

// 提交审批
const submitApprove = async () => {
  if (!currentLeave.value) return
  
  if (approveForm.result === 'rejected' && !approveForm.opinion) {
    ElMessage.warning('拒绝时必须填写审批意见')
    return
  }
  
  approving.value = true
  try {
    await axios.post('http://localhost:8000/api/leave/approve', {
      leave_id: currentLeave.value.id,
      result: approveForm.result,
      opinion: approveForm.opinion
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    
    ElMessage.success('审批完成')
    dialogVisible.value = false
    loadLeaves()
  } catch (error) {
    ElMessage.error('审批失败')
  } finally {
    approving.value = false
  }
}

// 批量审批 (仅演示逻辑)
const handleBatchApprove = () => {
  if (selectedLeaves.value.length === 0) return
  
  ElMessageBox.confirm(`确定要批量通过选中的 ${selectedLeaves.value.length} 条申请吗？`, '提示', {
    type: 'warning'
  }).then(async () => {
    // 实际应调用批量接口或循环调用
    ElMessage.success('批量审批成功 (演示)')
    loadLeaves()
  })
}

// 表格选择
const handleSelectionChange = (val: LeaveRecord[]) => {
  selectedLeaves.value = val
}

// 导出 Excel (演示)
const exportExcel = () => {
  ElMessage.success('正在导出 Excel...')
}

// 格式化时间
const formatTime = (iso: string) => {
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

// 计算时长
const calculateDuration = (start: string, end: string) => {
  const s = new Date(start).getTime()
  const e = new Date(end).getTime()
  const hours = (e - s) / (1000 * 3600)
  if (hours < 24) {
    return `${hours.toFixed(1)} 小时`
  } else {
    return `${(hours / 24).toFixed(1)} 天`
  }
}

const getStatusTag = (status: string) => {
  const map: Record<string, string> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
    recalled: 'info'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
    recalled: '已撤回'
  }
  return map[status] || status
}
</script>

<template>
  <div class="leave-approval-container">
    <div class="header-actions">
      <el-radio-group v-model="activeTab" style="margin-bottom: 20px">
        <el-radio-button label="pending">待审批</el-radio-button>
        <el-radio-button label="processed">已审批</el-radio-button>
        <el-radio-button label="all">全部记录</el-radio-button>
      </el-radio-group>
      
      <div class="filter-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索学生姓名/课程"
          :prefix-icon="Search"
          style="width: 200px; margin-right: 10px"
        />
        <el-select v-model="filterType" placeholder="请假类型" clearable style="width: 120px; margin-right: 10px">
          <el-option label="病假" value="病假" />
          <el-option label="事假" value="事假" />
          <el-option label="其他" value="其他" />
        </el-select>
        
        <el-button 
          v-if="activeTab === 'pending'" 
          type="success" 
          :disabled="selectedLeaves.length === 0"
          @click="handleBatchApprove"
        >
          批量通过
        </el-button>
        
        <el-button 
          v-if="activeTab === 'processed'" 
          type="primary" 
          :icon="Download"
          @click="exportExcel"
        >
          导出记录
        </el-button>
      </div>
    </div>
    
    <el-table 
      :data="filteredLeaves" 
      v-loading="loading" 
      style="width: 100%"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="55" v-if="activeTab === 'pending'" />
      <el-table-column prop="student_name" label="学生姓名" width="100" />
      <el-table-column prop="course_name" label="课程" width="150" />
      <el-table-column prop="type" label="类型" width="80" />
      <el-table-column label="请假时间" width="300">
        <template #default="{ row }">
          {{ formatTime(row.start_time) }} - {{ formatTime(row.end_time) }}
          <br>
          <small style="color: #909399">时长: {{ calculateDuration(row.start_time, row.end_time) }}</small>
        </template>
      </el-table-column>
      <el-table-column prop="create_time" label="提交时间" width="180">
        <template #default="{ row }">
          {{ formatTime(row.create_time) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusTag(row.status)">{{ getStatusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" fixed="right" width="100">
        <template #default="{ row }">
          <el-button 
            v-if="row.status === 'pending'" 
            type="primary" 
            link 
            size="small"
            @click="openApproveDialog(row)"
          >
            审批
          </el-button>
          <el-button v-else type="info" link size="small" @click="openApproveDialog(row)">
            详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 审批弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      title="请假审批"
      width="500px"
    >
      <div v-if="currentLeave" class="leave-detail">
        <div class="detail-item">
          <label>申请人：</label>
          <span>{{ currentLeave.student_name }}</span>
        </div>
        <div class="detail-item">
          <label>请假理由：</label>
          <p class="reason-text">{{ currentLeave.reason }}</p>
        </div>
        <div class="detail-item" v-if="currentLeave.file_url">
          <label>证明材料：</label>
          <a :href="currentLeave.file_url" target="_blank" class="file-link">查看附件</a>
        </div>
        
        <el-divider />
        
        <el-form v-if="currentLeave.status === 'pending'" label-position="top">
          <el-form-item label="审批结果">
            <el-radio-group v-model="approveForm.result">
              <el-radio label="approved">通过</el-radio>
              <el-radio label="rejected">拒绝</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="审批意见">
            <el-input 
              v-model="approveForm.opinion" 
              type="textarea" 
              :rows="3" 
              placeholder="请输入审批意见..."
            />
          </el-form-item>
        </el-form>
        
        <div v-else class="approved-info">
          <div class="detail-item">
            <label>审批结果：</label>
            <el-tag :type="getStatusTag(currentLeave.status)">{{ getStatusText(currentLeave.status) }}</el-tag>
          </div>
          <div class="detail-item">
            <label>审批意见：</label>
            <span>{{ currentLeave.opinion || '无' }}</span>
          </div>
        </div>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button 
            v-if="currentLeave?.status === 'pending'" 
            type="primary" 
            @click="submitApprove"
            :loading="approving"
          >
            确认提交
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.leave-approval-container {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 120px);
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
}

.filter-bar {
  display: flex;
  align-items: center;
}

.leave-detail {
  padding: 0 10px;
}

.detail-item {
  margin-bottom: 15px;
  display: flex;
}

.detail-item label {
  width: 80px;
  color: #909399;
  font-weight: 500;
}

.reason-text {
  margin: 0;
  flex: 1;
  background: #F5F7FA;
  padding: 10px;
  border-radius: 4px;
  font-size: 14px;
}

.file-link {
  color: #409EFF;
  text-decoration: none;
}

.file-link:hover {
  text-decoration: underline;
}
</style>
