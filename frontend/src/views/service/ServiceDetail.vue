<template>
  <div class="service-detail-container" v-loading="loading">
    <div class="header-breadcrumb">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/service/hall' }">办事大厅</el-breadcrumb-item>
        <el-breadcrumb-item>{{ service?.name }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div class="content-wrapper" v-if="service">
      <!-- 左侧：办事指南 -->
      <div class="left-panel">
        <div class="panel-card">
          <div class="service-header">
            <div class="icon-box">
              <el-icon><component :is="service.icon || 'Document'" /></el-icon>
            </div>
            <div class="title-info">
              <h1>{{ service.name }}</h1>
              <div class="meta">
                <el-tag>{{ service.category }}</el-tag>
                <el-tag type="info">办理时长：{{ service.processing_time }}</el-tag>
              </div>
            </div>
          </div>

          <el-divider />

          <div class="guide-section">
            <h3>办事指南</h3>
            <div class="rich-text" v-html="service.guide"></div>
          </div>

          <div class="guide-section">
            <h3>申请条件</h3>
            <div class="rich-text" v-html="service.apply_conditions"></div>
          </div>

          <div class="guide-section">
            <h3>所需材料</h3>
            <div class="materials-list">
              <div v-for="(mat, index) in service.required_materials" :key="index" class="material-item">
                <el-icon><Document /></el-icon>
                <span>{{ mat.name }}</span>
                <el-tag size="small" type="warning" v-if="mat.type === 'file'">需上传</el-tag>
              </div>
              <div v-if="!service.required_materials.length" class="no-data">无需材料</div>
            </div>
          </div>

          <div class="guide-section">
            <h3>办理流程</h3>
            <el-steps direction="vertical" :active="1">
              <el-step 
                v-for="(node, index) in service.process" 
                :key="index" 
                :title="node.node" 
                :description="node.desc" 
              />
            </el-steps>
          </div>
        </div>
      </div>

      <!-- 右侧：申请表单 -->
      <div class="right-panel">
        <div class="panel-card apply-card">
          <h3>在线申请</h3>
          <el-form 
            ref="formRef" 
            :model="formData" 
            :rules="formRules" 
            label-position="top"
            class="apply-form"
          >
            <!-- 动态表单字段 -->
            <template v-for="field in service.apply_fields" :key="field.name">
              <el-form-item 
                :label="field.name" 
                :prop="field.name"
                :required="field.required"
              >
                <!-- 输入框 -->
                <el-input 
                  v-if="field.type === 'input'" 
                  v-model="formData[field.name]" 
                  :placeholder="'请输入' + field.name" 
                />
                
                <!-- 文本域 -->
                <el-input 
                  v-if="field.type === 'textarea'" 
                  v-model="formData[field.name]" 
                  type="textarea" 
                  :rows="3" 
                  :placeholder="'请输入' + field.name" 
                />
                
                <!-- 下拉框 -->
                <el-select 
                  v-if="field.type === 'select'" 
                  v-model="formData[field.name]" 
                  :placeholder="'请选择' + field.name"
                  style="width: 100%"
                >
                  <el-option 
                    v-for="opt in field.options" 
                    :key="opt" 
                    :label="opt" 
                    :value="opt" 
                  />
                </el-select>
                
                <!-- 日期选择 -->
                <el-date-picker
                  v-if="field.type === 'datetime'"
                  v-model="formData[field.name]"
                  type="datetime"
                  placeholder="选择日期时间"
                  value-format="YYYY-MM-DD HH:mm:ss"
                  style="width: 100%"
                />
                
                <!-- 数字输入 -->
                <el-input-number 
                  v-if="field.type === 'number'" 
                  v-model="formData[field.name]" 
                  :min="1" 
                  style="width: 100%" 
                />
              </el-form-item>
            </template>

            <!-- 材料上传/文本填写 -->
            <div v-if="displayMaterials.length > 0" class="materials-upload-section">
              <h4>材料上传</h4>
              <div v-for="(mat, index) in displayMaterials" :key="'mat-'+index" class="upload-item">
                <div class="upload-label">{{ mat.name }} <span class="required">*</span></div>

                <!-- 文本材料 -->
                <el-input
                  v-if="mat.type === 'text'"
                  v-model="uploadedTexts[mat.name]"
                  type="textarea"
                  :rows="3"
                  :placeholder="mat.placeholder || '请输入材料内容'"
                />

                <!-- 文件材料 -->
                <el-upload
                  v-else
                  class="upload-demo"
                  action="/api/service/upload"
                  :headers="uploadHeaders"
                  :on-success="(res, file) => handleFileSuccess(res, file, mat.name)"
                  :before-upload="beforeUpload"
                  :limit="1"
                  :file-list="fileLists[mat.name] || []"
                  :show-file-list="true"
                >
                  <el-button type="primary" link>点击上传</el-button>
                  <template #tip>
                    <div class="el-upload__tip">支持 png/jpg/jpeg/pdf/doc/docx/xls/xlsx 文件，不超过 10MB</div>
                  </template>
                </el-upload>
              </div>
            </div>

            <div class="form-actions">
              <el-button @click="$router.back()">取消</el-button>
              <el-button type="primary" :loading="submitting" @click="submitApplication">提交申请</el-button>
            </div>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const serviceId = route.params.id
const service = ref<any>(null)
const loading = ref(true)
const submitting = ref(false)
const formRef = ref()
const formData = reactive<Record<string, any>>({})
const formRules = reactive<Record<string, any>>({})
const fileLists = reactive<Record<string, any[]>>({})
const uploadedFiles = reactive<Record<string, any>>({}) // 模拟文件上传结果
const uploadedTexts = reactive<Record<string, string>>({})
const uploadHeaders = {
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`
}

const displayMaterials = computed(() => {
  const mats = service.value?.required_materials || []
  if (mats.length > 0) return mats
  return [{ name: '上传材料', type: 'file', required: false, placeholder: '可上传证明材料（选填）' }]
})

const fetchDetail = async () => {
  try {
    const response = await axios.get(`/service/detail/${serviceId}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    service.value = response.data
    
    // 初始化表单校验规则
    service.value.apply_fields.forEach((field: any) => {
      if (field.required) {
        formRules[field.name] = [
          { required: true, message: `请输入${field.name}`, trigger: 'blur' }
        ]
      }
    })
  } catch (error) {
    console.error('获取详情失败', error)
    ElMessage.error('获取办事详情失败')
  } finally {
    loading.value = false
  }
}
const beforeUpload = (file: File) => {
  const limit = 10 * 1024 * 1024
  const allowed = ['image/png', 'image/jpeg', 'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
  if (file.size > limit) {
    ElMessage.error('文件大小不能超过10MB')
    return false
  }
  if (!allowed.includes(file.type)) {
    ElMessage.error('仅支持 png/jpg/jpeg/pdf/doc/docx/xls/xlsx')
    return false
  }
  return true
}

const handleFileSuccess = (res: any, file: any, matName: string) => {
  if (!res?.url) {
    ElMessage.error('文件上传失败')
    return
  }
  fileLists[matName] = [file]
  uploadedFiles[matName] = {
    name: res.name || file.name,
    url: res.url
  }
}

const submitApplication = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid: boolean) => {
    if (valid) {
      // 校验材料是否齐全（文本或文件），仅校验必填项
      const missingMaterials = displayMaterials.value.filter((mat: any) => {
        const required = mat.required !== false
        if (!required) return false
        if (mat.type === 'text') {
          return !uploadedTexts[mat.name]
        }
        return !uploadedFiles[mat.name]
      })
      if (missingMaterials.length > 0) {
        ElMessage.warning(`请上传: ${missingMaterials.map((m: any) => m.name).join(', ')}`)
        return
      }

      submitting.value = true
      try {
        const fileMaterials = Object.keys(uploadedFiles).map(key => ({
          name: key,
          type: 'file',
          ...uploadedFiles[key]
        }))

        const textMaterials = Object.keys(uploadedTexts).map(key => ({
          name: key,
          type: 'text',
          content: uploadedTexts[key]
        }))

        const materials = [...fileMaterials, ...textMaterials]

        await axios.post('/service/apply/submit', {
          item_id: service.value.id,
          form_data: formData,
          materials: materials
        }, {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        })
        
        ElMessageBox.alert(
          '您的申请已提交，请在“我的申请”中查看进度。',
          '提交成功',
          {
            type: 'success',
            confirmButtonText: '查看进度',
            callback: () => {
              router.push('/service/my-applications')
            }
          }
        )
      } catch (error) {
        console.error('提交失败', error)
        ElMessage.error('提交失败，请重试')
      } finally {
        submitting.value = false
      }
    }
  })
}

onMounted(() => {
  fetchDetail()
})
</script>

<style scoped>
.service-detail-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header-breadcrumb {
  margin-bottom: 20px;
}

.content-wrapper {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.left-panel {
  flex: 1;
}

.right-panel {
  width: 400px;
  position: sticky;
  top: 20px;
}

.panel-card {
  background: var(--el-bg-color-overlay);
  border-radius: 12px;
  padding: 30px;
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: var(--el-box-shadow-light);
}

.service-header {
  display: flex;
  gap: 20px;
  align-items: center;
}

.icon-box {
  width: 64px;
  height: 64px;
  background: var(--el-color-primary-light-9);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-color-primary);
  font-size: 32px;
}

.title-info h1 {
  margin: 0 0 10px;
  font-size: 24px;
  color: var(--el-text-color-primary);
}

.meta {
  display: flex;
  gap: 10px;
}

.guide-section {
  margin-top: 30px;
}

.guide-section h3 {
  font-size: 18px;
  color: var(--el-text-color-primary);
  margin-bottom: 15px;
  border-left: 4px solid var(--el-color-primary);
  padding-left: 10px;
}

.rich-text {
  color: var(--el-text-color-regular);
  line-height: 1.6;
}

.materials-list {
  background: var(--el-fill-color-light);
  padding: 15px;
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
}

.material-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--el-border-color);
}

.material-item:last-child {
  border-bottom: none;
}

.apply-card h3 {
  margin: 0 0 20px;
  font-size: 18px;
  text-align: center;
}

.materials-upload-section {
  margin-top: 20px;
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 20px;
}

.materials-upload-section h4 {
  margin: 0 0 15px;
}

.upload-item {
  margin-bottom: 15px;
}

.upload-label {
  font-size: 14px;
  margin-bottom: 5px;
  color: var(--el-text-color-regular);
}

.required {
  color: var(--el-color-danger);
}

.form-actions {
  margin-top: 30px;
  display: flex;
  justify-content: center;
  gap: 15px;
}

@media (max-width: 768px) {
  .content-wrapper {
    flex-direction: column;
  }
  .right-panel {
    width: 100%;
    position: static;
  }
}
</style>
