<script setup lang="ts">
/**
 * 学生作业管理页面
 * 包含：作业列表、提交作业、查看批改
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import axios from 'axios'

// --- 类型定义 ---
interface Homework {
  id: number
  title: string
  course_id: number
  course_name: string
  content: string
  deadline: string
  type: string
  score: number
  file_url?: string
  create_time: string
  // 附加提交状态
  submit_status?: '待提交' | '已提交' | '已批改' | '需重交'
  my_score?: number
  my_comment?: string
  submit_id?: number
}

// --- 状态管理 ---
const activeTab = ref('pending')
const homeworks = ref<Homework[]>([])
const loading = ref(false)

// 提交弹窗
const dialogVisible = ref(false)
const currentHomework = ref<Homework | null>(null)
const submitForm = reactive({
  content: '',
  file_url: ''
})
const submitting = ref(false)

// 查看详情弹窗
const detailVisible = ref(false)
const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }

// --- 初始化 ---
onMounted(() => {
  loadHomeworks()
})

const loadHomeworks = async () => {
  loading.value = true
  try {
    const res = await axios.get('/homework/list', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    // 模拟处理：实际后端返回的列表可能不包含提交状态，需要额外查询或后端聚合
    // 这里假设后端返回了基础信息，我们在前端模拟状态
    // 实际项目中应由后端聚合查询
    
    // 模拟数据增强
    const rawData = res.data
    // 模拟：给第一个作业标记为已批改，第二个为待提交
    if (rawData.length > 0) {
      rawData[0].submit_status = '待提交'
    }
    
    homeworks.value = rawData
  } catch (error) {
    // 模拟数据
    homeworks.value = [
      {
        id: 1,
        title: '第一章习题',
        course_id: 1,
        course_name: '高等数学',
        content: '完成课后习题 1-5 题',
        deadline: '2023-12-10T23:59:00',
        type: '主观题',
        score: 100,
        create_time: '2023-12-01T10:00:00',
        submit_status: '待提交'
      },
      {
        id: 2,
        title: 'Python大作业',
        course_id: 2,
        course_name: 'Python程序设计',
        content: '开发一个简单的爬虫',
        deadline: '2023-12-20T23:59:00',
        type: '文件提交',
        score: 100,
        create_time: '2023-12-05T10:00:00',
        submit_status: '已批改',
        my_score: 95,
        my_comment: '代码结构清晰',
        submit_id: 101
      }
    ]
  } finally {
    loading.value = false
  }
}

// 过滤列表
const filteredHomeworks = computed(() => {
  if (activeTab.value === 'pending') {
    return homeworks.value.filter(h => h.submit_status === '待提交' || h.submit_status === '需重交')
  } else {
    return homeworks.value.filter(h => h.submit_status !== '待提交' && h.submit_status !== '需重交')
  }
})

// 打开提交弹窗
const openSubmitDialog = (hw: Homework) => {
  currentHomework.value = hw
  submitForm.content = ''
  submitForm.file_url = ''
  dialogVisible.value = true
}

// 提交作业
const submitHomework = async () => {
  if (!currentHomework.value) return
  
  if (!submitForm.content && !submitForm.file_url) {
    ElMessage.warning('请输入内容或上传文件')
    return
  }
  
  submitting.value = true
  try {
    await axios.post('/homework/submit', {
      homework_id: currentHomework.value.id,
      content: submitForm.content,
      file_url: submitForm.file_url
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    
    ElMessage.success('提交成功')
    dialogVisible.value = false
    // 更新本地状态
    const idx = homeworks.value.findIndex(h => h.id === currentHomework.value?.id)
    if (idx !== -1) {
      homeworks.value[idx].submit_status = '已提交'
    }
  } catch (error) {
    ElMessage.error('提交失败')
  } finally {
    submitting.value = false
  }
}

// 查看详情
const viewDetail = (hw: Homework) => {
  currentHomework.value = hw
  detailVisible.value = true
}

// 文件上传成功
const handleUploadSuccess = (response: any) => {
  submitForm.file_url = response.url
  ElMessage.success('上传成功')
}

// 格式化时间
const formatTime = (iso: string) => {
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

const getStatusTag = (status?: string) => {
  const map: Record<string, string> = {
    '待提交': 'warning',
    '已提交': 'primary',
    '已批改': 'success',
    '需重交': 'danger'
  }
  return map[status || ''] || 'info'
}
</script>

<template>
  <div class="homework-container">
    <div class="header-actions">
      <el-radio-group v-model="activeTab" style="margin-bottom: 20px">
        <el-radio-button label="pending">待完成</el-radio-button>
        <el-radio-button label="completed">已完成</el-radio-button>
      </el-radio-group>
    </div>
    
    <el-table :data="filteredHomeworks" v-loading="loading" style="width: 100%">
      <el-table-column prop="title" label="作业标题" />
      <el-table-column prop="course_name" label="课程" width="150" />
      <el-table-column prop="type" label="类型" width="100" />
      <el-table-column label="截止时间" width="180">
        <template #default="{ row }">
          {{ formatTime(row.deadline) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusTag(row.submit_status)">{{ row.submit_status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button 
            v-if="row.submit_status === '待提交' || row.submit_status === '需重交'" 
            type="primary" 
            size="small"
            @click="openSubmitDialog(row)"
          >
            去提交
          </el-button>
          <el-button 
            v-else 
            type="info" 
            size="small"
            @click="viewDetail(row)"
          >
            查看
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 提交弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      title="提交作业"
      width="600px"
    >
      <div v-if="currentHomework" class="submit-form">
        <div class="hw-desc">
          <h4>{{ currentHomework.title }}</h4>
          <p class="desc-text">{{ currentHomework.content }}</p>
        </div>
        
        <el-form label-position="top">
          <el-form-item label="作业内容">
            <el-input 
              v-model="submitForm.content" 
              type="textarea" 
              :rows="6" 
              placeholder="请输入作业内容..."
            />
          </el-form-item>
          
          <el-form-item label="附件上传">
            <el-upload
              class="upload-demo"
              action="/api/leave/upload" 
              :headers="uploadHeaders"
              :on-success="handleUploadSuccess"
              :limit="1"
            >
              <el-button type="primary" :icon="UploadFilled">点击上传</el-button>
              <template #tip>
                <div class="el-upload__tip">支持 doc/pdf/zip 文件</div>
              </template>
            </el-upload>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitHomework" :loading="submitting">提交</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="作业详情"
      width="500px"
    >
      <div v-if="currentHomework" class="detail-content">
        <div class="detail-item">
          <label>作业标题：</label>
          <span>{{ currentHomework.title }}</span>
        </div>
        <div class="detail-item">
          <label>我的得分：</label>
          <span class="score" v-if="currentHomework.my_score">{{ currentHomework.my_score }}</span>
          <span v-else>暂无</span>
        </div>
        <div class="detail-item">
          <label>教师评语：</label>
          <p class="comment">{{ currentHomework.my_comment || '暂无评语' }}</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.homework-container {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 120px);
}

.hw-desc {
  background: #F5F7FA;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.hw-desc h4 {
  margin: 0 0 10px 0;
}

.desc-text {
  color: #606266;
  font-size: 14px;
  margin: 0;
}

.detail-item {
  margin-bottom: 15px;
}

.detail-item label {
  font-weight: bold;
  margin-right: 10px;
}

.score {
  color: #F56C6C;
  font-size: 18px;
  font-weight: bold;
}

.comment {
  background: #F0F9EB;
  padding: 10px;
  border-radius: 4px;
  color: #67C23A;
  margin-top: 5px;
}
</style>
