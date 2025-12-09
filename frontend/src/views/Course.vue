<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Plus, Delete, Upload, Download, Search, 
  Edit, View, DataLine, Reading, StarFilled 
} from '@element-plus/icons-vue'

// --- 1. 类型定义 ---
type CourseType = '必修' | '选修'
type ExamType = '考试' | '考查'

interface Course {
  id: number
  code: string
  name: string
  credits: number
  type: CourseType
  teacherId: string
  teacherName: string
  capacity: number
  enrolled: number
  intro?: string
  examType: ExamType
  isEvaluated: boolean
  satisfaction?: number
}

interface TeacherOption {
  id: string
  name: string
}

interface Evaluation {
  id: number
  studentName: string // 匿名显示为 "学生***"
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
const teacherOptions = ref<TeacherOption[]>([])
const teacherNameMap = reactive<Record<string, string>>({})

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`
})

const ensureTeacherOption = (id?: string, label?: string) => {
  if (!id) return
  if (!teacherNameMap[id]) {
    const name = label || id
    teacherNameMap[id] = name
    teacherOptions.value.push({ id, name })
  }
}

const syncTeacherNames = () => {
  courses.value = courses.value.map((course) => ({
    ...course,
    teacherName: teacherNameMap[course.teacherId] || course.teacherId || ''
  }))
}

const fetchTeachers = async () => {
  try {
    const res = await axios.get('http://localhost:8000/api/course/teachers', {
      headers: authHeaders()
    })
    teacherOptions.value = res.data
    Object.keys(teacherNameMap).forEach((key) => delete teacherNameMap[key])
    teacherOptions.value.forEach((t) => {
      teacherNameMap[t.id] = t.name
    })
    syncTeacherNames()
    if (!form.teacherId && teacherOptions.value.length > 0) {
      form.teacherId = teacherOptions.value[0].id
    }
  } catch (error: any) {
    teacherOptions.value = []
    const message = error?.response?.data?.detail || '无法加载教师列表'
    ElMessage.error(message)
  }
}

const fetchCourses = async () => {
  try {
    const res = await axios.get('http://localhost:8000/api/course/list', {
      headers: authHeaders()
    })
    courses.value = res.data.map((c: any) => ({
      id: c.id,
      code: `C-${String(1000 + c.id)}`,
      name: c.name,
      credits: c.credit,
      type: c.course_type,
      teacherId: c.teacher_id,
      teacherName: teacherNameMap[c.teacher_id] || c.teacher_id || '',
      capacity: c.capacity,
      enrolled: 0,
      intro: '',
      examType: '考试',
      isEvaluated: false,
      satisfaction: undefined
    }))
    courses.value.forEach((c) => ensureTeacherOption(c.teacherId, c.teacherName))
  } catch (e) {
    courses.value = []
  }
}

// --- 3. 状态管理 ---
const searchQuery = reactive({
  keyword: '',
  type: '',
  teacherId: ''
})
const loading = ref(false)
const selectedRows = ref<Course[]>([])

// 弹窗状态
const dialogVisible = ref(false)
const dialogType = ref<'add' | 'edit'>('add')
const evalDialogVisible = ref(false)
const currentCourse = ref<Course | null>(null)
const currentEvaluations = ref<Evaluation[]>([])

// 表单数据
const form = reactive({
  id: 0,
  code: '',
  name: '',
  credits: 3,
  type: '必修' as CourseType,
  teacherId: '',
  capacity: 60,
  intro: '',
  examType: '考试' as ExamType
})

// --- 4. 计算属性 ---

// 列表数据
const tableData = computed(() => {
  return courses.value.filter(item => {
    const matchKw = !searchQuery.keyword || 
      item.name.includes(searchQuery.keyword) || 
      item.code.includes(searchQuery.keyword)
    const matchType = !searchQuery.type || item.type === searchQuery.type
    const matchTeacher =
      !searchQuery.teacherId || item.teacherId === searchQuery.teacherId
    return matchKw && matchType && matchTeacher
  })
})

// 统计数据
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

const handleSelectionChange = (rows: Course[]) => {
  selectedRows.value = rows
}

// 新增/编辑
const handleAdd = () => {
  dialogType.value = 'add'
  Object.assign(form, {
    id: 0,
    code: `C-${Date.now().toString().slice(-4)}`, // 自动生成
    name: '',
    credits: 3,
    type: '必修',
    teacherId: teacherOptions.value[0]?.id || '',
    capacity: 60,
    intro: '',
    examType: '考试'
  })
  dialogVisible.value = true
}

const handleEdit = (row: Course) => {
  dialogType.value = 'edit'
  Object.assign(form, {
    id: row.id,
    code: row.code,
    name: row.name,
    credits: row.credits,
    type: row.type,
    teacherId: row.teacherId,
    capacity: row.capacity,
    intro: row.intro || '',
    examType: row.examType
  })
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.name || !form.teacherId) {
    ElMessage.warning('请填写完整信息')
    return
  }
  const teacherValid = teacherOptions.value.some((t) => t.id === form.teacherId)
  if (!teacherValid) {
    ElMessage.warning('请从下拉列表中选择已存在的授课教师')
    return
  }
  if (form.capacity < 20) {
    ElMessage.warning('课程容量不能少于 20')
    return
  }
  const payload = {
    name: form.name,
    credit: form.credits,
    teacher_id: form.teacherId,
    capacity: form.capacity,
    course_type: form.type
  }
  try {
    if (dialogType.value === 'add') {
      await axios.post('http://localhost:8000/api/course/add', payload, {
        headers: authHeaders()
      })
      ElMessage.success('添加成功')
    } else {
      await axios.put(`http://localhost:8000/api/course/${form.id}`, payload, {
        headers: authHeaders()
      })
      ElMessage.success('修改成功')
    }
    dialogVisible.value = false
    await fetchCourses()
  } catch (error: any) {
    const message = error?.response?.data?.detail || '操作失败，请稍后重试'
    ElMessage.error(message)
  }
}

// 删除
const handleDelete = (row: Course) => {
  if (row.enrolled > 0) {
    ElMessage.warning('该课程已有学生选课，不可删除')
    return
  }
  ElMessageBox.confirm('确定要删除该课程吗？', '提示', { type: 'warning' })
    .then(async () => {
      try {
        await axios.delete(`http://localhost:8000/api/course/${row.id}`, {
          headers: authHeaders()
        })
        ElMessage.success('删除成功')
        await fetchCourses()
      } catch (error: any) {
        const message = error?.response?.data?.detail || '删除失败'
        ElMessage.error(message)
      }
    })
}

// 批量删除
const handleBatchDelete = () => {
  if (selectedRows.value.length === 0) return ElMessage.warning('请选择课程')

  const hasEnrolled = selectedRows.value.some(r => r.enrolled > 0)
  if (hasEnrolled) {
    ElMessage.warning('选中的课程中包含已有学生选课的课程，无法批量删除')
    return
  }

  ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 门课程吗？`, '提示', { type: 'warning' })
    .then(async () => {
      try {
        await Promise.all(
          selectedRows.value.map(course =>
            axios.delete(`http://localhost:8000/api/course/${course.id}`, {
              headers: authHeaders()
            })
          )
        )
        ElMessage.success('批量删除成功')
        selectedRows.value = []
        await fetchCourses()
      } catch (error: any) {
        const message = error?.response?.data?.detail || '批量删除失败'
        ElMessage.error(message)
      }
    })
}

// 查看评估
const handleViewEvaluation = (row: Course) => {
  currentCourse.value = row
  currentEvaluations.value = []
  evalDialogVisible.value = true
}

// 导入导出
const handleImport = () => ElMessage.success('模拟导入成功')
const handleExport = () => ElMessage.success('模拟导出成功')

onMounted(async () => {
  await fetchTeachers()
  await fetchCourses()
})

</script>

<template>
  <div class="course-manage-container">
    <!-- 统计卡片 -->
    <div class="stat-section">
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="stat-card total">
            <div class="stat-icon"><el-icon><Reading /></el-icon></div>
            <div class="stat-info">
              <div class="label">总课程数</div>
              <div class="value">{{ statistics.total }}</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card type">
            <div class="stat-icon"><el-icon><DataLine /></el-icon></div>
            <div class="stat-info">
              <div class="label">必修 / 选修</div>
              <div class="value">{{ statistics.compulsory }} / {{ statistics.elective }}</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card evaluated">
            <div class="stat-icon"><el-icon><StarFilled /></el-icon></div>
            <div class="stat-info">
              <div class="label">已评估课程</div>
              <div class="value">{{ statistics.evaluated }}</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card satisfaction">
            <div class="stat-icon"><el-icon><StarFilled /></el-icon></div>
            <div class="stat-info">
              <div class="label">平均满意度</div>
              <div class="value">{{ statistics.avgSatisfaction }}</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 操作栏 -->
    <div class="action-bar">
      <div class="left-actions">
        <el-button type="primary" :icon="Plus" @click="handleAdd">新增课程</el-button>
        <el-button type="danger" :icon="Delete" plain @click="handleBatchDelete">批量删除</el-button>
        <el-button :icon="Upload" @click="handleImport">导入Excel</el-button>
        <el-button :icon="Download" @click="handleExport">导出Excel</el-button>
      </div>
      <div class="right-search">
        <el-input v-model="searchQuery.keyword" placeholder="课程名称/编号" :prefix-icon="Search" style="width: 180px" />
        <el-select v-model="searchQuery.type" placeholder="类型" clearable style="width: 100px">
          <el-option label="必修" value="必修" />
          <el-option label="选修" value="选修" />
        </el-select>
        <el-select v-model="searchQuery.teacherId" placeholder="授课教师" clearable style="width: 160px">
          <el-option v-for="t in teacherOptions" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
      </div>
    </div>

    <!-- 课程列表 -->
    <el-card shadow="never" class="table-card">
        <el-table
        :data="tableData"
        style="width: 100%"
        height="100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="code" label="编号" width="100" />
        <el-table-column prop="name" label="课程名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="credits" label="学分" width="80" align="center" />
        <el-table-column prop="type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.type === '必修' ? 'danger' : 'success'" size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="teacherName" label="授课教师" width="120" />
        <el-table-column label="选课情况" width="150">
          <template #default="{ row }">
            <el-progress 
              :percentage="Math.min(Math.round(row.enrolled / row.capacity * 100), 100)" 
              :status="row.enrolled >= row.capacity ? 'exception' : ''"
            >
              <template #default>
                <span :style="{ color: row.enrolled >= row.capacity ? '#F56C6C' : '' }">
                  {{ row.enrolled }}/{{ row.capacity }}
                </span>
              </template>
            </el-progress>
          </template>
        </el-table-column>
        <el-table-column label="评估状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.isEvaluated" type="success" effect="plain">已评估</el-tag>
            <el-tag v-else type="info" effect="plain">未评估</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Edit" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="primary" :icon="View" @click="handleViewEvaluation(row)" :disabled="!row.isEvaluated">评估</el-button>
            <el-button link type="danger" :icon="Delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogType === 'add' ? '新增课程' : '编辑课程'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="课程编号" required>
          <el-input v-model="form.code" :disabled="dialogType === 'edit'" />
        </el-form-item>
        <el-form-item label="课程名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="学分">
              <el-input-number v-model="form.credits" :min="1" :max="5" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="容量">
              <el-input-number v-model="form.capacity" :min="20" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="类型">
              <el-select v-model="form.type" style="width: 100%">
                <el-option label="必修" value="必修" />
                <el-option label="选修" value="选修" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="考核方式">
              <el-select v-model="form.examType" style="width: 100%">
                <el-option label="考试" value="考试" />
                <el-option label="考查" value="考查" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="授课教师" required>
          <el-select v-model="form.teacherId" style="width: 100%" placeholder="请选择授课教师">
            <el-option v-for="t in teacherOptions" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="课程简介">
          <el-input v-model="form.intro" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 评估详情弹窗 -->
    <el-dialog v-model="evalDialogVisible" title="课程评估详情" width="600px">
      <div v-if="currentCourse" class="eval-header">
        <div class="course-info">
          <h3>{{ currentCourse.name }}</h3>
          <p>授课教师：{{ currentCourse.teacherName }}</p>
        </div>
        <div class="total-score">
          <div class="score-val">{{ currentCourse.satisfaction }}</div>
          <el-rate v-model="currentCourse.satisfaction" disabled show-score text-color="#ff9900" />
        </div>
      </div>
      
      <div class="dimension-scores">
        <div class="dim-item">
          <span>教学质量</span>
          <el-progress :percentage="90" color="#67C23A" />
        </div>
        <div class="dim-item">
          <span>内容实用</span>
          <el-progress :percentage="85" color="#409EFF" />
        </div>
        <div class="dim-item">
          <span>难度适中</span>
          <el-progress :percentage="70" color="#E6A23C" />
        </div>
      </div>

      <el-divider content-position="left">学生评论</el-divider>
      
      <div class="comment-list">
        <div v-for="comment in currentEvaluations" :key="comment.id" class="comment-item">
          <div class="comment-top">
            <span class="student-name">{{ comment.studentName }}</span>
            <span class="comment-time">{{ comment.time }}</span>
          </div>
          <el-rate v-model="comment.score" disabled size="small" />
          <div class="comment-content">{{ comment.content }}</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.course-manage-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

/* 统计卡片 */
.stat-card {
  height: 100px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  color: #fff;
  transition: transform 0.3s;
}
.stat-card:hover { transform: translateY(-2px); }
.stat-card.total { background: linear-gradient(135deg, #409EFF, #79bbff); }
.stat-card.type { background: linear-gradient(135deg, #67C23A, #95d475); }
.stat-card.evaluated { background: linear-gradient(135deg, #E6A23C, #f3d19e); }
.stat-card.satisfaction { background: linear-gradient(135deg, #F56C6C, #fab6b6); }

.stat-icon { font-size: 40px; opacity: 0.8; margin-right: 15px; }
.stat-info .label { font-size: 14px; opacity: 0.9; }
.stat-info .value { font-size: 24px; font-weight: bold; }

/* 操作栏 */
.action-bar {
  display: flex;
  justify-content: space-between;
  background: #fff;
  padding: 15px;
  border-radius: 4px;
}
.right-search {
  display: flex;
  gap: 10px;
}

/* 表格 */
.table-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
:deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  padding: 0;
}

/* 评估详情 */
.eval-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
}
.total-score {
  text-align: center;
}
.score-val {
  font-size: 32px;
  font-weight: bold;
  color: #ff9900;
}
.dimension-scores {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}
.dim-item {
  flex: 1;
  text-align: center;
}
.dim-item span {
  font-size: 12px;
  color: #909399;
  display: block;
  margin-bottom: 5px;
}
.comment-list {
  max-height: 300px;
  overflow-y: auto;
}
.comment-item {
  border-bottom: 1px solid #ebeef5;
  padding: 10px 0;
}
.comment-top {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
  margin-bottom: 5px;
}
.comment-content {
  margin-top: 5px;
  color: #606266;
}
</style>
