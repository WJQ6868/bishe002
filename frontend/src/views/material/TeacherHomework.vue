<script setup lang="ts">
/**
 * 教师作业管理页面 (Material Design)
 * 包含：布置作业、作业列表、批改弹窗
 */
import { ref, reactive, onMounted, computed } from 'vue'
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
const createDialog = ref(false)
const createForm = reactive({
  title: '',
  course_id: undefined as number | undefined,
  content: '',
  deadline: null as Date | null,
  type: '主观题',
  score: 100,
  file_url: ''
})
const formValid = ref(false)

// 批改相关
const gradeDrawer = ref(false)
const currentHomework = ref<Homework | null>(null)
const submissions = ref<Submission[]>([])
const gradingSubmission = ref<Submission | null>(null)
const gradeDialog = ref(false)
const gradeForm = reactive({
  score: 0,
  comment: '',
  status: '已批改'
})

const snackbar = reactive({
  show: false,
  text: '',
  color: 'success'
})

const showSnackbar = (text: string, color: 'success' | 'error' | 'warning' = 'success') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

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
    const res = await axios.get('http://localhost:8000/api/homework/list', {
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
    return
  }
  
  try {
    await axios.post('http://localhost:8000/api/homework/create', {
        ...createForm,
        deadline: createForm.deadline?.toISOString()
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    createDialog.value = false
    loadHomeworks()
    // 重置表单
    createForm.title = ''
    createForm.content = ''
    showSnackbar('作业布置成功', 'success')
  } catch (error) {
    showSnackbar('布置失败，请重试', 'error')
  }
}

// 打开批改列表
const openGradeDrawer = (hw: Homework) => {
  currentHomework.value = hw
  gradeDrawer.value = true
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
  gradeDialog.value = true
}

// 提交评分
const submitGrade = async () => {
  if (!gradingSubmission.value) return
  
  try {
    await axios.post('http://localhost:8000/api/homework/grade', {
      submit_id: gradingSubmission.value.id,
      score: gradeForm.score,
      comment: gradeForm.comment,
      status: gradeForm.status
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    
    gradeDialog.value = false
    // 更新本地状态
    const idx = submissions.value.findIndex(s => s.id === gradingSubmission.value?.id)
    if (idx !== -1) {
      submissions.value[idx].status = gradeForm.status as any
      submissions.value[idx].score = gradeForm.score
      submissions.value[idx].comment = gradeForm.comment
    }
  } catch (error) {
    showSnackbar('批改失败，请重试', 'error')
  }
}

// 状态图标映射
const getStatusIcon = (status: string) => {
  const map: Record<string, string> = {
    '待提交': 'mdi-clock-outline', // pending
    '已提交': 'mdi-file-check-outline',
    '已批改': 'mdi-check-circle', // corrected
    '需重交': 'mdi-refresh' // redo
  }
  return map[status] || 'mdi-help-circle'
}

const getStatusColor = (status: string) => {
    const map: Record<string, string> = {
    '待提交': 'grey',
    '已提交': 'info',
    '已批改': 'success',
    '需重交': 'warning'
  }
  return map[status] || 'grey'
}

// 表格头
const submissionHeaders = [
    { title: '学生', key: 'student_name' },
    { title: '提交时间', key: 'submit_time' },
    { title: '状态', key: 'status' },
    { title: '分数', key: 'score' },
    { title: '操作', key: 'actions', sortable: false },
]
</script>

<template>
  <v-container fluid>
    <div class="d-flex align-center justify-space-between mb-4">
      <h2 class="text-h5 font-weight-bold">作业管理</h2>
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        elevation="2"
        @click="createDialog = true"
      >
        布置作业
      </v-btn>
    </div>

    <!-- 作业列表 -->
    <v-row>
      <v-col v-for="hw in homeworks" :key="hw.id" cols="12" md="6" lg="4">
        <v-card elevation="2" class="rounded-lg h-100 d-flex flex-column">
          <v-card-title class="d-flex justify-space-between align-start">
            <div class="text-truncate">{{ hw.title }}</div>
            <v-chip size="small" color="primary" label>{{ hw.course_name }}</v-chip>
          </v-card-title>
          
          <v-card-text class="flex-grow-1">
            <div class="text-body-2 text-grey mb-2">
              <v-icon size="small" class="mr-1">mdi-calendar-clock</v-icon>
              截止时间：{{ new Date(hw.deadline).toLocaleString() }}
            </div>
            <div class="text-body-1 text-truncate-2 mb-2">{{ hw.content }}</div>
            <v-divider class="my-2"></v-divider>
            <div class="d-flex justify-space-between text-caption text-grey">
                <span>总分: {{ hw.score }}</span>
                <span>类型: {{ hw.type }}</span>
            </div>
          </v-card-text>
          
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn
              variant="text"
              color="primary"
              prepend-icon="mdi-file-document-edit"
              @click="openGradeDrawer(hw)"
            >
              批改作业
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- 布置作业弹窗 -->
    <v-dialog v-model="createDialog" max-width="600">
      <v-card>
        <v-card-title>布置新作业</v-card-title>
        <v-card-text>
          <v-form v-model="formValid" @submit.prevent="submitCreate">
            <v-select
              v-model="createForm.course_id"
              :items="courses"
              item-title="name"
              item-value="id"
              label="课程"
              variant="outlined"
              prepend-inner-icon="mdi-book"
              :rules="[v => !!v || '请选择课程']"
            ></v-select>
            
            <v-text-field
              v-model="createForm.title"
              label="作业标题"
              variant="outlined"
              prepend-inner-icon="mdi-format-title"
              :rules="[v => !!v || '请输入标题']"
            ></v-text-field>
            
            <v-textarea
              v-model="createForm.content"
              label="作业内容"
              variant="outlined"
              prepend-inner-icon="mdi-text"
              rows="3"
            ></v-textarea>
            
            <v-row>
                <v-col cols="6">
                     <v-text-field
                        v-model="createForm.score"
                        label="总分"
                        type="number"
                        variant="outlined"
                        prepend-inner-icon="mdi-numeric"
                    ></v-text-field>
                </v-col>
                <v-col cols="6">
                     <v-select
                        v-model="createForm.type"
                        :items="['主观题', '客观题', '论文']"
                        label="类型"
                        variant="outlined"
                    ></v-select>
                </v-col>
            </v-row>
            
            <v-text-field
                v-model="createForm.deadline"
                label="截止时间"
                type="datetime-local"
                variant="outlined"
                prepend-inner-icon="mdi-calendar-clock"
            ></v-text-field>

          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="createDialog = false">取消</v-btn>
          <v-btn color="primary" variant="elevated" @click="submitCreate" :disabled="!formValid">布置</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 批改抽屉 -->
    <v-navigation-drawer
      v-model="gradeDrawer"
      location="right"
      width="600"
      temporary
    >
      <v-card flat class="h-100 d-flex flex-column">
        <v-toolbar color="primary" density="compact">
            <v-btn icon @click="gradeDrawer = false"><v-icon>mdi-close</v-icon></v-btn>
            <v-toolbar-title>{{ currentHomework?.title }} - 批改</v-toolbar-title>
        </v-toolbar>
        
        <v-card-text class="flex-grow-1 pa-0">
            <v-data-table
                :headers="submissionHeaders"
                :items="submissions"
                density="comfortable"
            >
                <template v-slot:item.status="{ item }">
                    <v-chip size="small" :color="getStatusColor(item.status)" label>
                        <v-icon start size="small">{{ getStatusIcon(item.status) }}</v-icon>
                        {{ item.status }}
                    </v-chip>
                </template>
                <template v-slot:item.actions="{ item }">
                    <v-btn
                        icon="mdi-pencil"
                        size="small"
                        variant="text"
                        color="primary"
                        @click="openGradeDialog(item)"
                    ></v-btn>
                </template>
            </v-data-table>
        </v-card-text>
      </v-card>
    </v-navigation-drawer>

    <!-- 评分弹窗 -->
    <v-dialog v-model="gradeDialog" max-width="500">
        <v-card>
            <v-card-title>作业评分</v-card-title>
            <v-card-text>
                <div class="mb-4">
                    <strong>学生提交内容：</strong>
                    <p class="text-body-2 bg-grey-lighten-4 pa-2 rounded">{{ gradingSubmission?.content }}</p>
                </div>
                
                <v-form @submit.prevent="submitGrade">
                    <v-text-field
                        v-model.number="gradeForm.score"
                        label="得分"
                        type="number"
                        variant="outlined"
                        prepend-inner-icon="mdi-star"
                    ></v-text-field>
                    
                    <v-textarea
                        v-model="gradeForm.comment"
                        label="评语"
                        variant="outlined"
                        prepend-inner-icon="mdi-comment-text"
                        rows="3"
                    ></v-textarea>
                    
                    <v-select
                        v-model="gradeForm.status"
                        :items="['已批改', '需重交']"
                        label="状态"
                        variant="outlined"
                    ></v-select>
                </v-form>
            </v-card-text>
            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn variant="text" @click="gradeDialog = false">取消</v-btn>
                <v-btn color="primary" variant="elevated" @click="submitGrade">确认</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      timeout="3000"
      location="top"
    >
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<style scoped>
.text-truncate-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
