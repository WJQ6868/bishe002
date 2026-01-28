<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, RefreshRight } from '@element-plus/icons-vue'
import {
  fetchColleges,
  fetchMajors,
  fetchAcademicClasses,
  updateAcademicClass,
  deleteAcademicClass,
  bindClassHeadTeacher,
  fetchAcademicStudents,
  updateAcademicStudent,
  deleteAcademicStudent,
  type AcademicClassItem,
  type AcademicStudentItem,
  type CollegeItem,
  type MajorItem,
} from '@/api/academic'
import axios from 'axios'

const colleges = ref<CollegeItem[]>([])
const majors = ref<MajorItem[]>([])
const classes = ref<AcademicClassItem[]>([])
const students = ref<AcademicStudentItem[]>([])

const loading = reactive({ colleges: false, majors: false })
const classLoading = ref(false)
const studentLoading = ref(false)

const selectedCollegeId = ref<number | null>(null)
const selectedMajorId = ref<number | null>(null)
const selectedClassId = ref<number | null>(null)

const teacherOptions = ref<{ teacher_no: string; name: string }[]>([])

const classDialog = reactive({ visible: false })
const classForm = reactive<{ id: number; major_id: number | null; name: string; code: string; status: number }>(
  {
    id: 0,
    major_id: null,
    name: '',
    code: '',
    status: 1,
  },
)

const bindDialog = reactive({ visible: false })
const bindForm = reactive<{ class_id: number; teacher_no: string }>(
  { class_id: 0, teacher_no: '' },
)

const studentDialog = reactive({ visible: false })
const studentForm = reactive<{ id: number; class_id: number | null; student_code: string; name: string; gender: number | null; mobile: string; status: number }>(
  {
    id: 0,
    class_id: null,
    student_code: '',
    name: '',
    gender: 1,
    mobile: '',
    status: 1,
  },
)
const studentFormRef = ref()

const genderName = (g: number | null | undefined) => {
  if (g === 1) return '男'
  if (g === 2) return '女'
  return ''
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const loadTeachers = async () => {
  try {
    const res = await axios.get('admin/teacher/list', { headers: getAuthHeaders() })
    teacherOptions.value = (res.data || []).map((t: any) => ({ teacher_no: t.teacher_no, name: t.name }))
  } catch {
    teacherOptions.value = []
  }
}

const loadColleges = async () => {
  loading.colleges = true
  try {
    const data = await fetchColleges()
    colleges.value = data
    if (!selectedCollegeId.value && data.length) selectedCollegeId.value = data[0].id
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取学院失败')
  } finally {
    loading.colleges = false
  }
}

const loadMajors = async () => {
  loading.majors = true
  try {
    if (!selectedCollegeId.value) {
      majors.value = []
      selectedMajorId.value = null
      classes.value = []
      selectedClassId.value = null
      students.value = []
      return
    }
    majors.value = await fetchMajors(selectedCollegeId.value)
    if (!selectedMajorId.value && majors.value.length) selectedMajorId.value = majors.value[0].id
    await loadClasses()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取专业失败')
  } finally {
    loading.majors = false
  }
}

const loadClasses = async () => {
  classLoading.value = true
  try {
    if (!selectedMajorId.value) {
      classes.value = []
      selectedClassId.value = null
      return
    }
    classes.value = await fetchAcademicClasses({ major_id: selectedMajorId.value })
    if (!selectedClassId.value && classes.value.length) selectedClassId.value = classes.value[0].id
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取班级失败')
    classes.value = []
  } finally {
    classLoading.value = false
  }
}

const loadStudents = async () => {
  studentLoading.value = true
  try {
    if (!selectedClassId.value) {
      students.value = []
      return
    }
    students.value = await fetchAcademicStudents({ class_id: selectedClassId.value })
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取学生失败')
    students.value = []
  } finally {
    studentLoading.value = false
  }
}

const onCollegeChange = async () => {
  selectedMajorId.value = null
  selectedClassId.value = null
  classes.value = []
  students.value = []
  await loadMajors()
}

const onMajorChange = async () => {
  selectedClassId.value = null
  students.value = []
  await loadClasses()
}

const onClassRowClick = (row: AcademicClassItem) => {
  selectedClassId.value = row.id
  loadStudents()
}

const onClassChange = async () => {
  await loadStudents()
}

const toggleClassStatus = async (row: AcademicClassItem) => {
  try {
    const next = row.status === 1 ? 0 : 1
    await updateAcademicClass(row.id, { status: next })
    row.status = next
    ElMessage.success(next === 1 ? '已启用' : '已停用')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '状态更新失败')
  }
}

const openEditClass = (row: AcademicClassItem) => {
  classDialog.visible = true
  Object.assign(classForm, {
    id: row.id,
    major_id: row.major_id,
    name: row.name,
    code: row.code || '',
    status: row.status,
  })
}

const submitClass = async () => {
  try {
    if (!classForm.major_id) {
      ElMessage.warning('请选择所属专业')
      return
    }
    await updateAcademicClass(classForm.id, {
      major_id: classForm.major_id,
      name: classForm.name,
      code: classForm.code,
      status: classForm.status,
    })
    ElMessage.success('班级已更新')
    classDialog.visible = false
    await loadClasses()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

const confirmDeleteClass = async (row: AcademicClassItem) => {
  try {
    await ElMessageBox.confirm(`确定删除班级「${row.name}」吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteAcademicClass(row.id)
    ElMessage.success('班级已删除')

    if (selectedClassId.value === row.id) {
      selectedClassId.value = null
      students.value = []
    }
    await loadClasses()
  } catch (e: any) {
    if (e === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

const openBindHeadTeacher = (row: AcademicClassItem) => {
  bindDialog.visible = true
  Object.assign(bindForm, {
    class_id: row.id,
    teacher_no: row.head_teacher_no || '',
  })
}

const submitBindHeadTeacher = async () => {
  try {
    const teacherNo = bindForm.teacher_no ? bindForm.teacher_no : null
    await bindClassHeadTeacher(bindForm.class_id, teacherNo)
    ElMessage.success('已绑定班主任')
    bindDialog.visible = false
    await loadClasses()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '绑定失败')
  }
}

const openEditStudent = (row: AcademicStudentItem) => {
  studentDialog.visible = true
  Object.assign(studentForm, {
    id: row.id,
    class_id: row.class_id,
    student_code: row.student_code,
    name: row.name,
    gender: row.gender,
    mobile: row.mobile,
    status: row.status,
  })
}

const submitStudent = async () => {
  if (!studentFormRef.value) return
  try {
    await updateAcademicStudent(studentForm.id, {
      class_id: studentForm.class_id || undefined,
      student_code: studentForm.student_code,
      name: studentForm.name,
      gender: studentForm.gender,
      mobile: studentForm.mobile,
      status: studentForm.status,
    })
    ElMessage.success('学生已更新')
    studentDialog.visible = false
    await loadStudents()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

const confirmRemoveStudent = async (row: AcademicStudentItem) => {
  try {
    await ElMessageBox.confirm(`确定移除学生「${row.name}（${row.student_code}）」吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteAcademicStudent(row.id)
    ElMessage.success('学生已移除')
    await loadStudents()
  } catch (e: any) {
    if (e === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || '移除失败')
  }
}

onMounted(async () => {
  await loadTeachers()
  await loadColleges()
  await loadMajors()
})
</script>

<template>
  <div class="page">
    <el-row :gutter="12" class="filter-row">
      <el-col :span="24">
        <div class="filters">
          <el-select
            v-model="selectedCollegeId"
            placeholder="选择学院"
            clearable
            style="width: 240px"
            @change="onCollegeChange"
          >
            <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>

          <el-select
            v-model="selectedMajorId"
            placeholder="选择专业"
            clearable
            style="width: 240px"
            @change="onMajorChange"
          >
            <el-option v-for="m in majors" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>

          <el-select
            v-model="selectedClassId"
            placeholder="选择班级"
            clearable
            style="width: 240px"
            @change="onClassChange"
          >
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="12">
      <el-col :span="12">
        <el-card class="equal-card">
          <div class="card-header">
            <span>班级</span>
          </div>
          <div class="table-area">
            <el-table
              :data="classes"
              v-loading="classLoading"
              style="width: 100%"
              size="small"
              height="100%"
              @row-click="onClassRowClick"
            >
              <el-table-column prop="name" label="班级名称" min-width="140" />
              <el-table-column prop="major_name" label="所属专业" min-width="140" />
              <el-table-column prop="code" label="班级编码" width="140" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '已启用' : '已停用' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="300" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" :icon="Edit" @click.stop="openEditClass(row)">编辑</el-button>
                  <el-button link type="warning" :icon="RefreshRight" @click.stop="toggleClassStatus(row)">
                    {{ row.status === 1 ? '停用' : '启用' }}
                  </el-button>
                  <el-button link type="primary" @click.stop="openBindHeadTeacher(row)">绑定班主任</el-button>
                  <el-button link type="danger" @click.stop="confirmDeleteClass(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="equal-card">
          <div class="card-header">
            <span>班级学生</span>
          </div>
          <div class="table-area">
            <el-table :data="students" v-loading="studentLoading" style="width: 100%" size="small" height="100%">
              <el-table-column prop="name" label="学生姓名" min-width="120" />
              <el-table-column prop="student_code" label="学号" width="110" />
              <el-table-column prop="class_name" label="所属班级" min-width="120" />
              <el-table-column label="性别" width="70">
                <template #default="{ row }">{{ genderName(row.gender) }}</template>
              </el-table-column>
              <el-table-column prop="mobile" label="联系方式" min-width="120" />
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '已启用' : '已停用' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" :icon="Edit" @click="openEditStudent(row)">编辑</el-button>
                  <el-button link type="danger" @click="confirmRemoveStudent(row)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="classDialog.visible" title="编辑班级" width="520px">
      <el-form :model="classForm" label-width="100px">
        <el-form-item label="所属专业" required>
          <el-select v-model="classForm.major_id" placeholder="选择专业" style="width: 100%">
            <el-option v-for="m in majors" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级名称" required>
          <el-input v-model="classForm.name" />
        </el-form-item>
        <el-form-item label="班级编码" required>
          <el-input v-model="classForm.code" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="classForm.status">
            <el-radio :value="1">已启用</el-radio>
            <el-radio :value="0">已停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="classDialog.visible = false">取消</el-button>
          <el-button type="primary" @click="submitClass">确定</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="bindDialog.visible" title="绑定班主任" width="520px">
      <el-form :model="bindForm" label-width="100px">
        <el-form-item label="班主任" required>
          <el-select v-model="bindForm.teacher_no" placeholder="选择班主任" style="width: 100%" filterable clearable>
            <el-option v-for="t in teacherOptions" :key="t.teacher_no" :label="`${t.name}（${t.teacher_no}）`" :value="t.teacher_no" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="bindDialog.visible = false">取消</el-button>
          <el-button type="primary" @click="submitBindHeadTeacher">确定</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="studentDialog.visible" title="编辑学生" width="520px">
      <el-form :model="studentForm" ref="studentFormRef" label-width="100px">
        <el-form-item label="所属班级" required>
          <el-select v-model="studentForm.class_id" placeholder="选择班级" style="width: 100%">
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学生姓名" required>
          <el-input v-model="studentForm.name" />
        </el-form-item>
        <el-form-item label="学号" required>
          <el-input v-model="studentForm.student_code" />
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="studentForm.gender">
            <el-radio :value="1">男</el-radio>
            <el-radio :value="2">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="studentForm.mobile" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="studentForm.status">
            <el-radio :value="1">已启用</el-radio>
            <el-radio :value="0">已停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="studentDialog.visible = false">取消</el-button>
          <el-button type="primary" @click="submitStudent">确定</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  padding: 12px;
}

.filter-row {
  margin-bottom: 12px;
}

.filters {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.equal-card {
  height: calc(50vh - 70px);
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
}

.table-area {
  flex: 1;
  overflow: auto;
}
</style>
