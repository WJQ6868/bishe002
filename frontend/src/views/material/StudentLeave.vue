<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useTheme } from 'vuetify'

const theme = useTheme()
const router = useRouter()
const formRef = ref<any>(null)
const valid = ref(false)
const submitting = ref(false)

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

// Form Data
const leaveType = ref(null)
const courseId = ref(null)
const dates = ref<any[]>([])
const reason = ref('')
const attachment = ref<File[]>([])
const teacherName = ref('李教授 (自动分配)') // Mock for now, or fetch based on course

// Data Options
const leaveTypes = [
  { title: '病假', value: 'sick', icon: 'mdi-hospital', color: 'red' },
  { title: '事假', value: 'personal', icon: 'mdi-home', color: 'orange' },
  { title: '其他', value: 'other', icon: 'mdi-help-circle', color: 'blue' }
]

const courses = ref<any[]>([])

// Validation Rules
const rules = {
  required: (v: any) => !!v || '此项必填',
  fileSize: (v: any) => !v || !v.length || v[0].size < 2000000 || '文件大小不能超过 2MB'
}

// Fetch Courses
const fetchCourses = async () => {
  try {
    const response = await axios.get('/course/list', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    courses.value = response.data.map((c: any) => ({
      title: c.name,
      value: c.id
    }))
  } catch (error) {
    showSnackbar('获取课程失败', 'error')
    courses.value = [
      { title: '高等数学', value: 1 },
      { title: '大学英语', value: 2 },
      { title: '计算机基础', value: 3 }
    ]
  }
}

const submitLeave = async () => {
  const { valid: isValid } = await formRef.value.validate()
  if (!isValid) return

  submitting.value = true
  try {
    const typeMap: Record<string, string> = { sick: '病假', personal: '事假', other: '其他' }
    const payload = {
      course_id: courseId.value,
      type: typeMap[leaveType.value as string] || '其他',
      start_time: new Date(dates.value[0]).toISOString(),
      end_time: new Date(dates.value[dates.value.length - 1]).toISOString(),
      reason: reason.value,
      file_url: undefined
    }
    await axios.post('/leave/apply', payload, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })

    // Reset
    formRef.value.reset()
    dates.value = []
    // Show success message (using snackbar ideally)
    showSnackbar('请假申请已提交', 'success')
  } catch (error) {
    showSnackbar('提交失败，请重试', 'error')
  } finally {
    submitting.value = false
  }
}

const resetForm = () => {
  formRef.value.reset()
  dates.value = []
}

onMounted(() => {
  fetchCourses()
})
</script>

<template>
  <v-container max-width="900" class="fill-height align-start">
    <v-card class="mx-auto w-100 rounded-xl" elevation="2">
      <v-card-title class="d-flex align-center py-4 px-6 bg-primary text-white">
        <v-icon icon="mdi-text-box-plus-outline" size="large" class="mr-3"></v-icon>
        <span class="text-h5 font-weight-bold">请假申请</span>
      </v-card-title>
      
      <v-divider></v-divider>

      <v-card-text class="pa-6">
        <v-form ref="formRef" v-model="valid" @submit.prevent="submitLeave">
          <v-row>
            <!-- Leave Type -->
            <v-col cols="12" md="6">
              <v-select
                v-model="leaveType"
                :items="leaveTypes"
                label="请假类型"
                variant="outlined"
                prepend-inner-icon="mdi-calendar-range"
                :rules="[rules.required]"
                item-title="title"
                item-value="value"
                color="primary"
              >
                <template v-slot:item="{ props, item }">
                  <v-list-item v-bind="props">
                    <template v-slot:prepend>
                      <v-icon :color="item.raw.color">{{ item.raw.icon }}</v-icon>
                    </template>
                  </v-list-item>
                </template>
                <template v-slot:selection="{ item }">
                  <div class="d-flex align-center">
                    <v-icon :color="item.raw.color" size="small" class="mr-2">{{ item.raw.icon }}</v-icon>
                    {{ item.title }}
                  </div>
                </template>
              </v-select>
            </v-col>

            <!-- Course -->
            <v-col cols="12" md="6">
              <v-autocomplete
                v-model="courseId"
                :items="courses"
                label="请假课程"
                variant="outlined"
                prepend-inner-icon="mdi-book-open-variant"
                :rules="[rules.required]"
                color="primary"
              ></v-autocomplete>
            </v-col>

            <!-- Date Picker -->
            <v-col cols="12">
              <div class="text-subtitle-1 mb-2 d-flex align-center text-grey-darken-1">
                <v-icon icon="mdi-clock-outline" class="mr-2"></v-icon>
                请假时间
              </div>
              <v-date-picker
                v-model="dates"
                color="primary"
                multiple="range"
                class="w-100 border rounded-lg"
                elevation="0"
              ></v-date-picker>
              <div class="text-caption text-grey mt-1" v-if="dates.length">
                已选: {{ dates.length }} 天
              </div>
            </v-col>

            <!-- Approval Teacher -->
            <v-col cols="12">
              <v-chip
                prepend-icon="mdi-account-circle"
                class="ma-0"
                color="grey-darken-1"
                variant="outlined"
              >
                审批教师: {{ teacherName }}
              </v-chip>
            </v-col>

            <!-- Reason -->
            <v-col cols="12">
              <v-textarea
                v-model="reason"
                label="请假理由"
                variant="outlined"
                prepend-inner-icon="mdi-comment-text-outline"
                :rules="[rules.required]"
                rows="4"
                counter
                color="primary"
                placeholder="请详细说明请假原因..."
              ></v-textarea>
            </v-col>

            <!-- Attachment -->
            <v-col cols="12">
              <v-file-input
                v-model="attachment"
                label="证明材料 (可选)"
                variant="outlined"
                prepend-inner-icon="mdi-attachment"
                accept="image/*,.pdf"
                :rules="[rules.fileSize]"
                show-size
                color="primary"
                chips
              ></v-file-input>
            </v-col>
          </v-row>

          <v-divider class="my-4"></v-divider>

          <div class="d-flex justify-end gap-4">
            <v-btn
              variant="outlined"
              size="large"
              class="mr-4"
              @click="resetForm"
              :disabled="submitting"
            >
              重置
            </v-btn>
            <v-btn
              type="submit"
              color="primary"
              variant="elevated"
              size="large"
              :loading="submitting"
              prepend-icon="mdi-send"
            >
              提交申请
            </v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>

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
