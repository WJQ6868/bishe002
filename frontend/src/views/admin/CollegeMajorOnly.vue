<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, RefreshRight } from '@element-plus/icons-vue'
import {
  fetchColleges,
  addCollege,
  updateCollege,
  deleteCollege,
  fetchMajors,
  addMajor,
  updateMajor,
  deleteMajor,
  type CollegeItem,
  type MajorItem,
} from '@/api/academic'

const colleges = ref<CollegeItem[]>([])
const majors = ref<MajorItem[]>([])
const loading = reactive({ colleges: false, majors: false })

const selectedCollegeId = ref<number | null>(null)

const collegeDialog = reactive({ visible: false, isEdit: false })
const collegeForm = reactive({ id: 0, name: '', code: '', status: 1 })
const collegeRules = {
  name: [{ required: true, message: '请输入学院名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入学院编码', trigger: 'blur' }],
}
const collegeFormRef = ref()

const batchDialog = reactive({ visible: false })
const batchMajors = ref<{ name: string; code: string; status: number }[]>([])

const loadColleges = async () => {
  loading.colleges = true
  try {
    const data = await fetchColleges()
    colleges.value = data
    if (!selectedCollegeId.value && data.length) {
      selectedCollegeId.value = data[0].id
    }
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
      return
    }
    majors.value = await fetchMajors(selectedCollegeId.value)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取专业失败')
    majors.value = []
  } finally {
    loading.majors = false
  }
}

const onCollegeChange = async () => {
  await loadMajors()
}

const openAddCollege = () => {
  collegeDialog.visible = true
  collegeDialog.isEdit = false
  Object.assign(collegeForm, { id: 0, name: '', code: '', status: 1 })
}

const openEditCollege = (row: CollegeItem) => {
  collegeDialog.visible = true
  collegeDialog.isEdit = true
  Object.assign(collegeForm, { id: row.id, name: row.name, code: row.code, status: row.status })
}

const submitCollege = async () => {
  if (!collegeFormRef.value) return
  await collegeFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    try {
      if (collegeDialog.isEdit) {
        await updateCollege(collegeForm.id, { name: collegeForm.name, code: collegeForm.code, status: collegeForm.status })
        ElMessage.success('学院已更新')
      } else {
        await addCollege({ name: collegeForm.name, code: collegeForm.code, status: collegeForm.status })
        ElMessage.success('学院已新增')
      }
      collegeDialog.visible = false
      await loadColleges()
      await loadMajors()
    } catch (e: any) {
      ElMessage.error(e?.response?.data?.detail || '操作失败')
    }
  })
}

const toggleCollegeStatus = async (row: CollegeItem) => {
  try {
    const next = row.status === 1 ? 0 : 1
    await updateCollege(row.id, { status: next })
    row.status = next
    ElMessage.success(next === 1 ? '已启用' : '已停用')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '状态更新失败')
  }
}

const confirmDeleteCollege = async (row: CollegeItem) => {
  try {
    await ElMessageBox.confirm(`确定删除学院「${row.name}」吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteCollege(row.id)
    ElMessage.success('学院已删除')

    if (selectedCollegeId.value === row.id) {
      selectedCollegeId.value = null
      majors.value = []
    }
    await loadColleges()
    await loadMajors()
  } catch (e: any) {
    if (e === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

const toggleMajorStatus = async (row: MajorItem) => {
  try {
    const next = row.status === 1 ? 0 : 1
    await updateMajor(row.id, { status: next })
    row.status = next
    ElMessage.success(next === 1 ? '已启用' : '已停用')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '状态更新失败')
  }
}

const confirmDeleteMajor = async (row: MajorItem) => {
  try {
    await ElMessageBox.confirm(`确定删除专业「${row.name}」吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteMajor(row.id)
    ElMessage.success('专业已删除')
    await loadMajors()
  } catch (e: any) {
    if (e === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

const openBatchMajor = () => {
  if (!selectedCollegeId.value) {
    ElMessage.warning('请先选择学院')
    return
  }
  batchDialog.visible = true
  batchMajors.value = [{ name: '', code: '', status: 1 }]
}

const addBatchRow = () => {
  batchMajors.value.push({ name: '', code: '', status: 1 })
}

const removeBatchRow = (index: number) => {
  batchMajors.value.splice(index, 1)
}

const submitMajors = async () => {
  if (!selectedCollegeId.value) {
    ElMessage.warning('请先选择学院')
    return
  }
  const payloads = batchMajors.value
    .map((m) => ({ name: (m.name || '').trim(), code: (m.code || '').trim(), status: m.status }))
    .filter((m) => m.name && m.code)

  if (!payloads.length) {
    ElMessage.warning('请至少填写一行专业名称与编码')
    return
  }

  try {
    for (const m of payloads) {
      await addMajor({ ...m, college_id: selectedCollegeId.value })
    }
    ElMessage.success('专业已新增')
    batchDialog.visible = false
    await loadMajors()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '提交失败')
  }
}

onMounted(async () => {
  await loadColleges()
  await loadMajors()
})
</script>

<template>
  <div class="page">
    <el-row :gutter="12">
      <el-col :span="12">
        <el-card class="equal-card">
          <div class="card-header">
            <span>学院列表</span>
            <div class="actions">
              <el-button type="primary" :icon="Plus" @click="openAddCollege">新增学院</el-button>
            </div>
          </div>
          <div class="table-area">
            <el-table :data="colleges" v-loading="loading.colleges" style="width: 100%" size="small" height="100%">
              <el-table-column prop="name" label="学院名称" min-width="180" />
              <el-table-column prop="code" label="编码" width="120" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '已启动' : '已停用' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="220" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" :icon="Edit" @click="openEditCollege(row)">编辑</el-button>
                  <el-button link type="warning" :icon="RefreshRight" @click="toggleCollegeStatus(row)">
                    {{ row.status === 1 ? '停用' : '启用' }}
                  </el-button>
                  <el-button link type="danger" @click="confirmDeleteCollege(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="equal-card">
          <div class="card-header">
            <div>
              <span>专业列表</span>
              <el-select
                v-model="selectedCollegeId"
                placeholder="选择学院"
                clearable
                style="margin-left: 12px; width: 220px"
                @change="onCollegeChange"
              >
                <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </div>
            <div class="actions">
              <el-button type="primary" :icon="Plus" @click="openBatchMajor">批量新增专业</el-button>
            </div>
          </div>
          <div class="table-area">
            <el-table :data="majors" v-loading="loading.majors" style="width: 100%" size="small" height="100%">
              <el-table-column prop="name" label="专业名称" min-width="180" />
              <el-table-column prop="code" label="编码" width="120" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-switch v-model="row.status" :active-value="1" :inactive-value="0" @change="() => toggleMajorStatus(row)" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="160" fixed="right">
                <template #default="{ row }">
                  <el-button link type="warning" :icon="RefreshRight" @click="toggleMajorStatus(row)">
                    {{ row.status === 1 ? '停用' : '启用' }}
                  </el-button>
                  <el-button link type="danger" @click="confirmDeleteMajor(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="collegeDialog.visible" :title="collegeDialog.isEdit ? '编辑学院' : '新增学院'" width="520px">
      <el-form :model="collegeForm" :rules="collegeRules" ref="collegeFormRef" label-width="100px">
        <el-form-item label="学院名称" prop="name">
          <el-input v-model="collegeForm.name" />
        </el-form-item>
        <el-form-item label="学院编码" prop="code">
          <el-input v-model="collegeForm.code" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="collegeForm.status">
            <el-radio :value="1">已启动</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="collegeDialog.visible = false">取消</el-button>
          <el-button type="primary" @click="submitCollege">确定</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="batchDialog.visible" title="批量新增专业" width="720px">
      <div class="batch-tip">所属学院：
        <strong>{{ colleges.find(c => c.id === selectedCollegeId)?.name || '未选择' }}</strong>
      </div>
      <el-table :data="batchMajors" size="small" style="width: 100%">
        <el-table-column label="#" width="50">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column label="专业名称" min-width="200">
          <template #default="{ row }">
            <el-input v-model="row.name" placeholder="请输入专业名称" />
          </template>
        </el-table-column>
        <el-table-column label="编码" min-width="140">
          <template #default="{ row }">
            <el-input v-model="row.code" placeholder="请输入编码" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ $index }">
            <el-button link type="danger" @click="removeBatchRow($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="batch-actions">
        <el-button type="primary" :icon="Plus" plain @click="addBatchRow">新增一行</el-button>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="batchDialog.visible = false">取消</el-button>
          <el-button type="primary" @click="submitMajors">提交</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  padding: 12px;
}

.equal-card {
  height: calc(100vh - 160px);
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
}

.actions {
  display: flex;
  gap: 8px;
}

.table-area {
  flex: 1;
  overflow: auto;
}

.batch-tip {
  margin-bottom: 12px;
}

.batch-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-start;
}
</style>
