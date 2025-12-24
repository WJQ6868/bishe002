<script setup lang="ts">
/**
 * 学生作业管理页面 (Material Design 适配版)
 * 包含：作业列表、提交作业、查看批改
 * 
 * Material Design 适配说明：
 * 1. 使用 v-data-table 替代 el-table，支持响应式和分页
 * 2. 使用 v-dialog 和 v-card 实现弹窗和卡片布局，elevation 体现层级
 * 3. 使用 v-tabs 替代 el-radio-group，符合 Material 导航规范
 * 4. 状态使用 v-chip 配合 mdi 图标，色彩遵循 Material 3 规范
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
const search = ref('')

// 提交弹窗
const dialogVisible = ref(false)
const currentHomework = ref<Homework | null>(null)
const submitForm = reactive({
  content: '',
  file_url: null as File[] | null // Vuetify v-file-input 返回 File[]
})
const submitting = ref(false)
const snackbar = ref({
  show: false,
  text: '',
  color: 'success'
})

// 查看详情弹窗
const detailVisible = ref(false)

// --- 表格配置 ---
const headers = [
  { title: '作业标题', key: 'title', align: 'start' },
  { title: '课程', key: 'course_name', align: 'start' },
  { title: '类型', key: 'type', align: 'center' },
  { title: '截止时间', key: 'deadline', align: 'center' },
  { title: '状态', key: 'submit_status', align: 'center' },
  { title: '操作', key: 'actions', align: 'center', sortable: false }
] as const

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
    // 模拟数据增强
    const rawData = res.data
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
  submitForm.file_url = null
  dialogVisible.value = true
}

// 提交作业
const submitHomework = async () => {
  if (!currentHomework.value) return
  
  // 简单校验
  if (!submitForm.content && (!submitForm.file_url || submitForm.file_url.length === 0)) {
    showSnackbar('请输入内容或上传文件', 'warning')
    return
  }
  
  submitting.value = true
  try {
    // 处理文件上传
    let uploadedUrl = ''
    if (submitForm.file_url && submitForm.file_url.length > 0) {
      const formData = new FormData()
      formData.append('file', submitForm.file_url[0])
      const uploadRes = await axios.post('/leave/upload', formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          Authorization: `Bearer ${localStorage.getItem('token')}` 
        }
      })
      uploadedUrl = uploadRes.data.url
    }

    await axios.post('/homework/submit', {
      homework_id: currentHomework.value.id,
      content: submitForm.content,
      file_url: uploadedUrl
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    
    showSnackbar('提交成功', 'success')
    dialogVisible.value = false
    // 更新本地状态
    const idx = homeworks.value.findIndex(h => h.id === currentHomework.value?.id)
    if (idx !== -1) {
      homeworks.value[idx].submit_status = '已提交'
    }
  } catch (error) {
    showSnackbar('提交失败', 'error')
  } finally {
    submitting.value = false
  }
}

// 查看详情
const viewDetail = (hw: Homework) => {
  currentHomework.value = hw
  detailVisible.value = true
}

// 格式化时间
const formatTime = (iso: string) => {
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

// 状态颜色映射
const getStatusColor = (status?: string) => {
  const map: Record<string, string> = {
    '待提交': 'warning',
    '已提交': 'primary',
    '已批改': 'success',
    '需重交': 'error'
  }
  return map[status || ''] || 'grey'
}

// 状态图标映射
const getStatusIcon = (status?: string) => {
  const map: Record<string, string> = {
    '待提交': 'mdi-clock-outline',
    '已提交': 'mdi-check-circle-outline',
    '已批改': 'mdi-checkbox-marked-circle-outline',
    '需重交': 'mdi-alert-circle-outline'
  }
  return map[status || ''] || 'mdi-help-circle-outline'
}

const showSnackbar = (text: string, color: string) => {
  snackbar.value = { show: true, text, color }
}
</script>

<template>
  <v-container fluid class="fill-height align-start pa-0">
    <v-row>
      <v-col cols="12">
        <v-card class="mx-4 mt-4" elevation="2">
          <v-card-title class="d-flex align-center py-3">
            <v-icon icon="mdi-book-edit-outline" class="mr-2" color="primary"></v-icon>
            我的作业
            <v-spacer></v-spacer>
            <v-text-field
              v-model="search"
              append-inner-icon="mdi-magnify"
              label="搜索作业"
              single-line
              hide-details
              density="compact"
              variant="outlined"
              class="max-width-300"
            ></v-text-field>
          </v-card-title>

          <v-tabs v-model="activeTab" color="primary">
            <v-tab value="pending">
              <v-icon start>mdi-timer-sand</v-icon>
              待完成
            </v-tab>
            <v-tab value="completed">
              <v-icon start>mdi-check-all</v-icon>
              已完成
            </v-tab>
          </v-tabs>

          <v-divider></v-divider>

          <v-data-table
            :headers="headers"
            :items="filteredHomeworks"
            :search="search"
            :loading="loading"
            hover
          >
            <!-- 截止时间列 -->
            <template v-slot:item.deadline="{ item }">
              {{ formatTime(item.deadline) }}
            </template>

            <!-- 状态列 -->
            <template v-slot:item.submit_status="{ item }">
              <v-chip
                :color="getStatusColor(item.submit_status)"
                label
                size="small"
                class="font-weight-medium"
              >
                <v-icon start size="small">{{ getStatusIcon(item.submit_status) }}</v-icon>
                {{ item.submit_status }}
              </v-chip>
            </template>

            <!-- 操作列 -->
            <template v-slot:item.actions="{ item }">
              <v-btn
                v-if="item.submit_status === '待提交' || item.submit_status === '需重交'"
                color="primary"
                variant="elevated"
                size="small"
                prepend-icon="mdi-pencil"
                @click="openSubmitDialog(item)"
              >
                去提交
              </v-btn>
              <v-btn
                v-else
                color="info"
                variant="tonal"
                size="small"
                prepend-icon="mdi-eye"
                @click="viewDetail(item)"
              >
                查看
              </v-btn>
            </template>
            
            <template v-slot:no-data>
              <div class="text-center pa-4">
                <v-icon size="large" color="grey-lighten-1">mdi-file-document-outline</v-icon>
                <div class="text-grey mt-2">暂无作业数据</div>
              </div>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>

    <!-- 提交作业弹窗 -->
    <v-dialog v-model="dialogVisible" max-width="600px" persistent transition="dialog-bottom-transition">
      <v-card v-if="currentHomework">
        <v-toolbar color="primary" density="compact">
          <v-toolbar-title>提交作业</v-toolbar-title>
          <v-btn icon @click="dialogVisible = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-toolbar>
        
        <v-card-text class="pa-4">
          <div class="bg-grey-lighten-4 pa-4 rounded mb-4">
            <div class="text-subtitle-1 font-weight-bold mb-1">{{ currentHomework.title }}</div>
            <div class="text-body-2 text-grey-darken-1">{{ currentHomework.content }}</div>
          </div>

          <v-form>
            <v-textarea
              v-model="submitForm.content"
              label="作业内容"
              variant="outlined"
              rows="5"
              prepend-inner-icon="mdi-text-box-edit-outline"
              placeholder="请输入作业内容..."
              class="mb-2"
            ></v-textarea>

            <v-file-input
              v-model="submitForm.file_url"
              label="附件上传"
              variant="outlined"
              prepend-icon=""
              prepend-inner-icon="mdi-paperclip"
              accept=".doc,.docx,.pdf,.zip,.rar"
              show-size
              hint="支持 doc/pdf/zip 文件"
              persistent-hint
            ></v-file-input>
          </v-form>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn variant="text" color="grey-darken-1" @click="dialogVisible = false">取消</v-btn>
          <v-btn 
            color="primary" 
            variant="elevated" 
            @click="submitHomework" 
            :loading="submitting"
            prepend-icon="mdi-send"
          >
            提交
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 作业详情弹窗 -->
    <v-dialog v-model="detailVisible" max-width="500px" transition="scale-transition">
      <v-card v-if="currentHomework">
        <v-card-title class="d-flex align-center bg-primary text-white py-3">
          <v-icon icon="mdi-file-document-check-outline" class="mr-2"></v-icon>
          作业详情
          <v-spacer></v-spacer>
          <v-btn icon density="compact" variant="text" @click="detailVisible = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text class="pa-4">
          <v-list density="compact">
            <v-list-item>
              <template v-slot:prepend>
                <v-icon color="primary">mdi-book-open-variant</v-icon>
              </template>
              <v-list-item-title class="font-weight-bold">作业标题</v-list-item-title>
              <v-list-item-subtitle class="text-body-1 text-high-emphasis mt-1">
                {{ currentHomework.title }}
              </v-list-item-subtitle>
            </v-list-item>
            
            <v-divider class="my-2"></v-divider>
            
            <v-list-item>
              <template v-slot:prepend>
                <v-icon color="error">mdi-scoreboard</v-icon>
              </template>
              <v-list-item-title class="font-weight-bold">我的得分</v-list-item-title>
              <v-list-item-subtitle class="mt-1">
                <span v-if="currentHomework.my_score" class="text-h5 font-weight-bold text-error">
                  {{ currentHomework.my_score }}
                </span>
                <span v-else class="text-grey">暂无评分</span>
              </v-list-item-subtitle>
            </v-list-item>

            <v-divider class="my-2"></v-divider>

            <v-list-item>
              <template v-slot:prepend>
                <v-icon color="success">mdi-comment-quote-outline</v-icon>
              </template>
              <v-list-item-title class="font-weight-bold">教师评语</v-list-item-title>
              <v-sheet class="bg-green-lighten-5 pa-3 rounded mt-2 text-body-2 text-green-darken-2">
                {{ currentHomework.my_comment || '暂无评语' }}
              </v-sheet>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- 全局提示 -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000" location="top">
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<style scoped>
.max-width-300 {
  max-width: 300px;
}
</style>
