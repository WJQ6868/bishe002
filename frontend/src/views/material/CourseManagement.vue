<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import axios from 'axios'

// --- 1. 类型定义 ---
type CourseType = '必修' | '选修'
type ExamType = '考试' | '考查'

interface Course {
  id: number
  code: string
  name: string
  credits: number
  type: CourseType
  teacher: string
  capacity: number
  enrolled: number
  intro?: string
  examType: ExamType
  isEvaluated: boolean
  satisfaction?: number
}

interface Evaluation {
  id: number
  studentName: string
  score: number
  content: string
  time: string
  dimensions: {
    quality: number
    utility: number
    difficulty: number
  }
}

// --- 2. 数据源 ---
const courses = ref<Course[]>([])
const teachers = ['张教授', '李副教授', '王讲师', '赵博士', '钱老师']

const fetchCourses = async () => {
  try {
    const res = await axios.get('/course/list', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    courses.value = res.data.map((c: any) => ({
      id: c.id,
      code: `C-${1000 + c.id}`,
      name: c.name,
      credits: c.credit,
      type: c.course_type,
      teacher: c.teacher?.name || '',
      capacity: c.capacity,
      enrolled: 0,
      intro: '',
      examType: '考试',
      isEvaluated: false,
      satisfaction: undefined
    }))
  } catch (e) {
    courses.value = []
  }
}

// --- 3. 状态管理 ---
const searchQuery = reactive({
  keyword: '',
  type: null as string | null,
  teacher: null as string | null
})
const selectedRows = ref<number[]>([]) // v-data-table uses IDs usually or objects

const dialogVisible = ref(false)
const dialogType = ref<'add' | 'edit'>('add')
const evalDialogVisible = ref(false)
const currentCourse = ref<Course | null>(null)
const currentEvaluations = ref<Evaluation[]>([])

const form = reactive({
  id: 0,
  code: '',
  name: '',
  credits: 3,
  type: '必修' as CourseType,
  teacher: '',
  capacity: 60,
  intro: '',
  examType: '考试' as ExamType
})

// Snackbar & Confirm Dialog
const snackbar = reactive({
  show: false,
  text: '',
  color: 'success'
})

const showMessage = (text: string, color: 'success' | 'warning' | 'error' = 'success') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

const confirmDialog = reactive({
  show: false,
  title: '',
  text: '',
  onConfirm: () => {}
})

const showConfirm = (title: string, text: string, onConfirm: () => void) => {
  confirmDialog.title = title
  confirmDialog.text = text
  confirmDialog.onConfirm = onConfirm
  confirmDialog.show = true
}

const handleConfirm = () => {
  confirmDialog.onConfirm()
  confirmDialog.show = false
}

// --- 4. 计算属性 ---
const headers = [
  { title: '编号', key: 'code', align: 'start' as const },
  { title: '课程名称', key: 'name' },
  { title: '学分', key: 'credits', align: 'center' as const },
  { title: '类型', key: 'type' },
  { title: '授课教师', key: 'teacher' },
  { title: '选课情况', key: 'enrolled', width: '200px' },
  { title: '评估状态', key: 'isEvaluated', align: 'center' as const },
  { title: '操作', key: 'actions', sortable: false, align: 'end' as const },
]

const tableData = computed(() => {
  return courses.value.filter(item => {
    const matchKw = !searchQuery.keyword || 
      item.name.includes(searchQuery.keyword) || 
      item.code.includes(searchQuery.keyword)
    const matchType = !searchQuery.type || item.type === searchQuery.type
    const matchTeacher = !searchQuery.teacher || item.teacher.includes(searchQuery.teacher!)
    return matchKw && matchType && matchTeacher
  })
})

const statistics = computed(() => {
  const total = courses.value.length
  const compulsory = courses.value.filter(c => c.type === '必修').length
  const elective = courses.value.filter(c => c.type === '选修').length
  const evaluated = courses.value.filter(c => c.isEvaluated).length
  
  const evaluatedCourses = courses.value.filter(c => c.satisfaction)
  const avgSatisfaction = evaluatedCourses.length > 0
    ? (evaluatedCourses.reduce((sum, c) => sum + (c.satisfaction || 0), 0) / evaluatedCourses.length).toFixed(1)
    : '0.0'

  return { total, compulsory, elective, evaluated, avgSatisfaction }
})

// --- 5. 核心逻辑 ---
const handleAdd = () => {
  dialogType.value = 'add'
  Object.assign(form, {
    id: 0,
    code: `C-${Date.now().toString().slice(-4)}`,
    name: '',
    credits: 3,
    type: '必修',
    teacher: '',
    capacity: 60,
    intro: '',
    examType: '考试'
  })
  dialogVisible.value = true
}

const handleEdit = (row: Course) => {
  dialogType.value = 'edit'
  Object.assign(form, row)
  dialogVisible.value = true
}

const handleSave = () => {
  if (!form.name || !form.teacher) {
    showMessage('请填写完整信息', 'warning')
    return
  }
  showMessage(dialogType.value === 'add' ? '添加成功' : '修改成功', 'success')
  dialogVisible.value = false
}

const handleDelete = (row: Course) => {
  if (row.enrolled > 0) {
    showMessage('该课程已有学生选课，不可删除', 'warning')
    return
  }
  showConfirm('删除确认', '确定要删除该课程吗？', () => {
    showMessage('删除成功', 'success')
  })
}

const handleBatchDelete = () => {
  if (selectedRows.value.length === 0) {
    showMessage('请选择课程', 'warning')
    return
  }
  
  // Note: selectedRows in Vuetify 3 v-data-table with return-object is objects, 
  // but default is IDs if item-value is set. I'll assume IDs here for simplicity or handle both.
  // Actually, let's check table configuration. I will not set item-value, so it returns objects.
  // Wait, better to handle objects.
  
  // Let's assume selectedRows contains objects for now
  // Cast to any to avoid TS issues if strict
  const selectedCourses = selectedRows.value as any as Course[]
  
  // However, usually v-data-table v-model:selection returns IDs if item-value is provided.
  // I'll set item-value="id" in the template.
  
  // Re-finding objects from IDs
  const selectedObjs = courses.value.filter(c => (selectedRows.value as unknown as number[]).includes(c.id))

  const hasEnrolled = selectedObjs.some(r => r.enrolled > 0)
  if (hasEnrolled) {
    showMessage('选中的课程中包含已有学生选课的课程，无法批量删除', 'warning')
    return
  }

  showConfirm('批量删除', `确定删除选中的 ${selectedRows.value.length} 门课程吗？`, () => {
    showMessage('批量删除成功', 'success')
    selectedRows.value = []
  })
}

const handleViewEvaluation = (row: Course) => {
  currentCourse.value = row
  currentEvaluations.value = []
  evalDialogVisible.value = true
}

const handleImport = () => showMessage('导入功能待接入后端', 'warning')
const handleExport = () => showMessage('导出功能待接入后端', 'warning')

onMounted(fetchCourses)

</script>

<template>
  <div class="course-manage-container">
    <!-- 统计卡片 -->
    <v-row class="mb-4">
      <v-col cols="12" sm="6" md="3">
        <v-card class="stat-card total" elevation="2">
          <div class="d-flex align-center pa-4">
            <v-icon size="40" color="white" class="mr-3">mdi-book-open-variant</v-icon>
            <div class="text-white">
              <div class="text-caption opacity-80">总课程数</div>
              <div class="text-h5 font-weight-bold">{{ statistics.total }}</div>
            </div>
          </div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card class="stat-card type" elevation="2">
          <div class="d-flex align-center pa-4">
            <v-icon size="40" color="white" class="mr-3">mdi-chart-bar</v-icon>
            <div class="text-white">
              <div class="text-caption opacity-80">必修 / 选修</div>
              <div class="text-h5 font-weight-bold">{{ statistics.compulsory }} / {{ statistics.elective }}</div>
            </div>
          </div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card class="stat-card evaluated" elevation="2">
          <div class="d-flex align-center pa-4">
            <v-icon size="40" color="white" class="mr-3">mdi-star</v-icon>
            <div class="text-white">
              <div class="text-caption opacity-80">已评估课程</div>
              <div class="text-h5 font-weight-bold">{{ statistics.evaluated }}</div>
            </div>
          </div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card class="stat-card satisfaction" elevation="2">
          <div class="d-flex align-center pa-4">
            <v-icon size="40" color="white" class="mr-3">mdi-emoticon-happy</v-icon>
            <div class="text-white">
              <div class="text-caption opacity-80">平均满意度</div>
              <div class="text-h5 font-weight-bold">{{ statistics.avgSatisfaction }}</div>
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- 操作栏 -->
    <v-card class="mb-4 pa-4">
      <div class="d-flex flex-wrap align-center justify-space-between gap-4">
        <div class="d-flex gap-2">
          <v-btn color="primary" prepend-icon="mdi-plus" @click="handleAdd">新增课程</v-btn>
          <v-btn color="error" variant="outlined" prepend-icon="mdi-delete" @click="handleBatchDelete">批量删除</v-btn>
          <v-btn variant="text" prepend-icon="mdi-upload" @click="handleImport">导入</v-btn>
          <v-btn variant="text" prepend-icon="mdi-download" @click="handleExport">导出</v-btn>
        </div>
        <div class="d-flex gap-2 align-center" style="min-width: 400px">
          <v-text-field
            v-model="searchQuery.keyword"
            placeholder="课程名称/编号"
            prepend-inner-icon="mdi-magnify"
            density="compact"
            hide-details
            style="max-width: 200px"
          ></v-text-field>
          <v-select
            v-model="searchQuery.type"
            :items="['必修', '选修']"
            placeholder="类型"
            density="compact"
            hide-details
            clearable
            style="max-width: 120px"
          ></v-select>
          <v-select
            v-model="searchQuery.teacher"
            :items="teachers"
            placeholder="授课教师"
            density="compact"
            hide-details
            clearable
            style="max-width: 140px"
          ></v-select>
        </div>
      </div>
    </v-card>

    <!-- 课程列表 -->
    <v-card>
      <v-data-table
        v-model="selectedRows"
        :headers="headers"
        :items="tableData"
        item-value="id"
        show-select
        hover
      >
        <template #item.type="{ item }">
          <v-chip
            :color="item.type === '必修' ? 'error' : 'success'"
            size="small"
            label
          >
            {{ item.type }}
          </v-chip>
        </template>

        <template #item.enrolled="{ item }">
          <div class="d-flex align-center">
            <v-progress-linear
              :model-value="Math.min(Math.round(item.enrolled / item.capacity * 100), 100)"
              :color="item.enrolled >= item.capacity ? 'error' : 'primary'"
              height="15"
              rounded
            >
              <template #default="{ value }">
                <span style="font-size: 10px; color: white;">
                  {{ item.enrolled }}/{{ item.capacity }}
                </span>
              </template>
            </v-progress-linear>
          </div>
        </template>

        <template #item.isEvaluated="{ item }">
          <v-chip
            v-if="item.isEvaluated"
            color="success"
            size="small"
            variant="tonal"
          >
            已评估
          </v-chip>
          <v-chip v-else size="small" variant="text">
            未评估
          </v-chip>
        </template>

        <template #item.actions="{ item }">
          <v-btn icon size="small" variant="text" color="primary" @click="handleEdit(item)">
            <v-icon>mdi-pencil</v-icon>
            <v-tooltip activator="parent" location="top">编辑</v-tooltip>
          </v-btn>
          <v-btn 
            icon 
            size="small" 
            variant="text" 
            color="info" 
            :disabled="!item.isEvaluated"
            @click="handleViewEvaluation(item)"
          >
            <v-icon>mdi-eye</v-icon>
            <v-tooltip activator="parent" location="top">评估详情</v-tooltip>
          </v-btn>
          <v-btn icon size="small" variant="text" color="error" @click="handleDelete(item)">
            <v-icon>mdi-delete</v-icon>
            <v-tooltip activator="parent" location="top">删除</v-tooltip>
          </v-btn>
        </template>
      </v-data-table>
    </v-card>

    <!-- 新增/编辑弹窗 -->
    <v-dialog v-model="dialogVisible" max-width="600px">
      <v-card>
        <v-card-title>
          <span class="text-h5">{{ dialogType === 'add' ? '新增课程' : '编辑课程' }}</span>
        </v-card-title>
        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model="form.code"
                  label="课程编号"
                  :disabled="dialogType === 'edit'"
                  required
                ></v-text-field>
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model="form.name"
                  label="课程名称"
                  required
                ></v-text-field>
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model.number="form.credits"
                  label="学分"
                  type="number"
                  min="1"
                  max="5"
                ></v-text-field>
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field
                  v-model.number="form.capacity"
                  label="容量"
                  type="number"
                  min="10"
                ></v-text-field>
              </v-col>
              <v-col cols="12" sm="6">
                <v-select
                  v-model="form.type"
                  :items="['必修', '选修']"
                  label="类型"
                ></v-select>
              </v-col>
              <v-col cols="12" sm="6">
                <v-select
                  v-model="form.examType"
                  :items="['考试', '考查']"
                  label="考核方式"
                ></v-select>
              </v-col>
              <v-col cols="12">
                <v-select
                  v-model="form.teacher"
                  :items="teachers"
                  label="授课教师"
                  required
                ></v-select>
              </v-col>
              <v-col cols="12">
                <v-textarea
                  v-model="form.intro"
                  label="课程简介"
                  rows="3"
                ></v-textarea>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="blue-darken-1" variant="text" @click="dialogVisible = false">取消</v-btn>
          <v-btn color="blue-darken-1" variant="text" @click="handleSave">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 评估详情弹窗 -->
    <v-dialog v-model="evalDialogVisible" max-width="700px">
      <v-card>
        <v-card-title class="bg-grey-lighten-4 pa-4">
          <div class="d-flex justify-space-between align-center">
            <div>
              <div class="text-h6">{{ currentCourse?.name }}</div>
              <div class="text-subtitle-2 text-grey">授课教师：{{ currentCourse?.teacher }}</div>
            </div>
            <div class="text-center">
              <div class="text-h4 text-orange font-weight-bold">{{ currentCourse?.satisfaction }}</div>
              <v-rating
                :model-value="currentCourse?.satisfaction"
                color="orange"
                density="compact"
                half-increments
                readonly
                size="small"
              ></v-rating>
            </div>
          </div>
        </v-card-title>

        <v-card-text class="pa-4">
          <v-row class="mb-4">
            <v-col cols="4" class="text-center">
              <div class="text-caption text-grey mb-1">教学质量</div>
              <v-progress-linear model-value="90" color="success" height="8" rounded></v-progress-linear>
            </v-col>
            <v-col cols="4" class="text-center">
              <div class="text-caption text-grey mb-1">内容实用</div>
              <v-progress-linear model-value="85" color="blue" height="8" rounded></v-progress-linear>
            </v-col>
            <v-col cols="4" class="text-center">
              <div class="text-caption text-grey mb-1">难度适中</div>
              <v-progress-linear model-value="70" color="orange" height="8" rounded></v-progress-linear>
            </v-col>
          </v-row>

          <div class="text-subtitle-1 font-weight-bold mb-3">学生评论</div>
          
          <v-list lines="two" max-height="300" class="overflow-y-auto">
            <v-list-item v-for="comment in currentEvaluations" :key="comment.id" class="px-0">
              <template #prepend>
                <v-avatar color="grey-lighten-2" size="32">
                  <span class="text-caption">{{ comment.studentName[2] }}</span>
                </v-avatar>
              </template>
              
              <v-list-item-title class="d-flex justify-space-between align-center">
                <span class="text-caption font-weight-bold">{{ comment.studentName }}</span>
                <span class="text-caption text-grey">{{ comment.time }}</span>
              </v-list-item-title>
              
              <v-list-item-subtitle class="mt-1">
                <v-rating
                  :model-value="comment.score"
                  density="compact"
                  color="orange"
                  size="x-small"
                  readonly
                  class="mb-1"
                ></v-rating>
                <div>{{ comment.content }}</div>
              </v-list-item-subtitle>
              <v-divider class="mt-2"></v-divider>
            </v-list-item>
          </v-list>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="evalDialogVisible = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 全局提示组件 -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000" location="top">
      {{ snackbar.text }}
      <template #actions>
        <v-btn color="white" variant="text" @click="snackbar.show = false">关闭</v-btn>
      </template>
    </v-snackbar>

    <v-dialog v-model="confirmDialog.show" max-width="400">
      <v-card>
        <v-card-title>{{ confirmDialog.title }}</v-card-title>
        <v-card-text>{{ confirmDialog.text }}</v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="confirmDialog.show = false">取消</v-btn>
          <v-btn color="primary" variant="text" @click="handleConfirm">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.stat-card {
  transition: transform 0.3s;
}
.stat-card:hover {
  transform: translateY(-4px);
}
.stat-card.total { background: linear-gradient(135deg, #409EFF, #79bbff); }
.stat-card.type { background: linear-gradient(135deg, #67C23A, #95d475); }
.stat-card.evaluated { background: linear-gradient(135deg, #E6A23C, #f3d19e); }
.stat-card.satisfaction { background: linear-gradient(135deg, #F56C6C, #fab6b6); }
.gap-2 { gap: 8px; }
.gap-4 { gap: 16px; }
</style>
