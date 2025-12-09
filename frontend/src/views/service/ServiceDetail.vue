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
                <el-tag type="info">办理时长: {{ service.processing_time }}</el-tag>
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
            <template v-for="(field, index) in service.apply_fields" :key="index">
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

            <!-- 材料上传 -->
            <div v-if="service.required_materials.length > 0" class="materials-upload-section">
              <h4>材料上传</h4>
              <div v-for="(mat, index) in service.required_materials" :key="'mat-'+index" class="upload-item">
                <div class="upload-label">{{ mat.name }} <span class="required">*</span></div>
                <el-upload
                  class="upload-demo"
                  action="#"
                  :auto-upload="false"
                  :on-change="(file) => handleFileChange(file, mat.name)"
                  :limit="1"
                  :file-list="fileLists[mat.name] || []"
                >
                  <el-button type="primary" link>点击上传</el-button>
                  <template #tip>
                    <div class="el-upload__tip">支持 jpg/png/pdf 文件，不超过 5MB</div>
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
import { ref, onMounted, reactive } from 'vue'
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

const fetchDetail = async () => {
  try {
    const response = await axios.get(`http://localhost:8000/api/service/detail/${serviceId}`, {
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

const handleFileChange = (file: any, matName: string) => {
  // 模拟文件上传，实际应上传到服务器获取 URL
  // 这里直接存储文件名作为演示
  fileLists[matName] = [file]
  uploadedFiles[matName] = {
    name: file.name,
    url: URL.createObjectURL(file.raw) // 仅用于演示
  }
}

const submitApplication = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid: boolean) => {
    if (valid) {
      // 校验材料是否齐全
      const missingMaterials = service.value.required_materials.filter((mat: any) => !uploadedFiles[mat.name])
      if (missingMaterials.length > 0) {
        ElMessage.warning(`请上传: ${missingMaterials.map((m: any) => m.name).join(', ')}`)
        return
      }

      submitting.value = true
      try {
        const materials = Object.keys(uploadedFiles).map(key => ({
          name: key,
          ...uploadedFiles[key]
        }))

        await axios.post('http://localhost:8000/api/service/apply/submit', {
          item_id: service.value.id,
          form_data: formData,
          materials: materials
        }, {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        })
        
        ElMessageBox.success({
          title: '提交成功',
          message: '您的申请已提交，请在"我的申请"中查看进度',
          confirmButtonText: '查看进度',
          callback: () => {
            router.push('/service/my-applications')
          }
        })
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
  background: white;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.service-header {
  display: flex;
  gap: 20px;
  align-items: center;
}

.icon-box {
  width: 64px;
  height: 64px;
  background: #ecf5ff;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
  font-size: 32px;
}

.title-info h1 {
  margin: 0 0 10px;
  font-size: 24px;
  color: #303133;
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
  color: #303133;
  margin-bottom: 15px;
  border-left: 4px solid #409eff;
  padding-left: 10px;
}

.rich-text {
  color: #606266;
  line-height: 1.6;
}

.materials-list {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
}

.material-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px dashed #dcdfe6;
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
  border-top: 1px solid #ebeef5;
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
  color: #606266;
}

.required {
  color: #f56c6c;
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
