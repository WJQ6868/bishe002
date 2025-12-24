<script setup lang="ts">
/**
 * 教师作业管理页面
 * 包含：布置作业、作业列表、批改弹窗
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Download } from '@element-plus/icons-vue'
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
}

interface Submission {
  id: number
  student_id: number
  student_name: string
  content: string
  file_url?: string
  submit_time: string
  status: '待提交' | '已提交' | '已批改' | '需重交'
  score?: number
  comment?: string
}

interface CourseOption {
  id: number
  name: string
}

// --- 状态管理 ---
const activeTab = ref('list')
const homeworks = ref<Homework[]>([])
const loading = ref(false)
const courses = ref<CourseOption[]>([])

// 布置作业表单
const createForm = reactive({
  title: '',
  course_id: undefined as number | undefined,
  content: '',
  deadline: '',
  type: '主观题',
  score: 100,
  file_url: ''
})

// 批改相关
const drawerVisible = ref(false)
const currentHomework = ref<Homework | null>(null)
const submissions = ref<Submission[]>([])
const gradingSubmission = ref<Submission | null>(null)
const gradeDialogVisible = ref(false)
const gradeForm = reactive({
  score: 0,
  comment: '',
  status: '已批改'
})

// --- 初始化 ---
onMounted(() => {
  loadCourses()
  loadHomeworks()
})

const loadCourses = async () => {
  // 模拟数据
  courses.value = [
    { id: 1, name: '高等数学' },
    { id: 2, name: 'Python程序设计' }
  ]
}

const loadHomeworks = async () => {
  loading.value = true
  try {
    const res = await axios.get('/homework/list', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    homeworks.value = res.data
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
        create_time: '2023-12-01T10:00:00'
      }
    ]
  } finally {
    loading.value = false
  }
}

// 提交布置作业
const submitCreate = async () => {
  if (!createForm.title || !createForm.course_id || !createForm.deadline) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  try {
    await axios.post('/homework/create', createForm, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    ElMessage.success('布置成功')
    activeTab.value = 'list'
    loadHomeworks()
    // 重置表单
    createForm.title = ''
    createForm.content = ''
  } catch (error) {
    ElMessage.error('布置失败')
  }
}

// 打开批改列表
const openGradeDrawer = (hw: Homework) => {
  currentHomework.value = hw
  drawerVisible.value = true
  loadSubmissions(hw.id)
}

// 加载提交记录 (模拟)
const loadSubmissions = (hwId: number) => {
  // 模拟数据
  submissions.value = [
    {
      id: 1,
      student_id: 2001,
      student_name: '王同学',
      content: '已完成，请老师查阅',
      submit_time: '2023-12-05T10:00:00',
      status: '已提交'
    },
    {
      id: 2,
      student_id: 2002,
      student_name: '李同学',
      content: '附件已上传',
      submit_time: '2023-12-05T11:00:00',
      status: '已批改',
      score: 95,
      comment: '做得不错'
    }
  ]
}

// 打开评分弹窗
const openGradeDialog = (sub: Submission) => {
  gradingSubmission.value = sub
  gradeForm.score = sub.score || 0
  gradeForm.comment = sub.comment || ''
  gradeForm.status = sub.status === '已批改' ? '已批改' : '已批改'
  gradeDialogVisible.value = true
}

// 提交评分
const submitGrade = async () => {
  if (!gradingSubmission.value) return
  
  try {
    await axios.post('/homework/grade', {
      submit_id: gradingSubmission.value.id,
      score: gradeForm.score,
      comment: gradeForm.comment,
      status: gradeForm.status
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    
    ElMessage.success('批改完成')
    gradeDialogVisible.value = false
    // 更新本地状态
    const idx = submissions.value.findIndex(s => s.id === gradingSubmission.value?.id)
    if (idx !== -1) {
      submissions.value[idx].status = gradeForm.status as any
      submissions.value[idx].score = gradeForm.score
      submissions.value[idx].comment = gradeForm.comment
    }
  } catch (error) {
    ElMessage.error('批改失败')
  }
}

// 格式化时间
const formatTime = (iso: string) => {
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

const getStatusTag = (status: string) => {
  const map: Record<string, string> = {
    '待提交': 'info',
    '已提交': 'primary',
    '已批改': 'success',
    '需重交': 'danger'
  }
  return map[status] || 'info'
}
</script>

<template>
  <div class="homework-container">
    <div class="header-actions">
      <el-radio-group v-model="activeTab" style="margin-bottom: 20px">
        <el-radio-button label="list">作业列表</el-radio-button>
        <el-radio-button label="create">布置作业</el-radio-button>
      </el-radio-group>
    </div>
    
    <!-- 作业列表 -->
    <div v-if="activeTab === 'list'" class="list-panel">
      <el-table :data="homeworks" v-loading="loading" style="width: 100%">
        <el-table-column prop="title" label="作业标题" />
        <el-table-column prop="course_name" label="所属课程" width="150" />
        <el-table-column prop="type" label="类型" width="100" />
        <el-table-column label="截止时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.deadline) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="primary" link @click="openGradeDrawer(row)">批改</el-button>
            <el-button type="danger" link>删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    
    <!-- 布置作业 -->
    <div v-if="activeTab === 'create'" class="create-panel">
      <el-form :model="createForm" label-width="100px" style="max-width: 800px">
        <el-form-item label="作业标题" required>
          <el-input v-model="createForm.title" placeholder="请输入作业标题" />
        </el-form-item>
        
        <el-form-item label="所属课程" required>
          <el-select v-model="createForm.course_id" placeholder="选择课程">
            <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="截止时间" required>
          <el-date-picker
            v-model="createForm.deadline"
            type="datetime"
            placeholder="选择截止时间"
          />
        </el-form-item>
        
        <el-form-item label="作业类型">
          <el-radio-group v-model="createForm.type">
            <el-radio label="主观题">主观题</el-radio>
            <el-radio label="客观题">客观题</el-radio>
            <el-radio label="文件提交">文件提交</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="作业内容">
          <el-input 
            v-model="createForm.content" 
            type="textarea" 
            :rows="6" 
            placeholder="请输入作业内容要求..."
          />
        </el-form-item>
        
        <el-form-item label="总分">
          <el-input-number v-model="createForm.score" :min="0" :max="100" />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="submitCreate">立即布置</el-button>
          <el-button @click="activeTab = 'list'">取消</el-button>
        </el-form-item>
      </el-form>
    </div>
    
    <!-- 批改抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="作业批改"
      size="60%"
    >
      <div v-if="currentHomework" class="drawer-content">
        <div class="hw-info">
          <h3>{{ currentHomework.title }}</h3>
          <p>截止时间：{{ formatTime(currentHomework.deadline) }}</p>
        </div>
        
        <el-table :data="submissions" style="width: 100%">
          <el-table-column prop="student_name" label="姓名" width="100" />
          <el-table-column prop="submit_time" label="提交时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.submit_time) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusTag(row.status)">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="score" label="得分" width="80" />
          <el-table-column label="操作">
            <template #default="{ row }">
              <el-button type="primary" link @click="openGradeDialog(row)">评分</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
    
    <!-- 评分弹窗 -->
    <el-dialog
      v-model="gradeDialogVisible"
      title="作业评分"
      width="500px"
    >
      <div v-if="gradingSubmission" class="grade-detail">
        <div class="detail-item">
          <label>学生提交：</label>
          <div class="content-box">{{ gradingSubmission.content }}</div>
        </div>
        
        <el-divider />
        
        <el-form :model="gradeForm" label-width="80px">
          <el-form-item label="得分">
            <el-input-number v-model="gradeForm.score" :min="0" :max="100" />
          </el-form-item>
          <el-form-item label="评语">
            <el-input 
              v-model="gradeForm.comment" 
              type="textarea" 
              :rows="3" 
              placeholder="请输入评语..."
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-radio-group v-model="gradeForm.status">
              <el-radio label="已批改">通过</el-radio>
              <el-radio label="需重交">打回重交</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="gradeDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitGrade">确认</el-button>
        </span>
      </template>
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

.create-panel {
  padding: 20px;
  background: #F5F7FA;
  border-radius: 4px;
}

.hw-info {
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #EBEEF5;
}

.content-box {
  background: #F5F7FA;
  padding: 10px;
  border-radius: 4px;
  min-height: 60px;
}
</style>
