<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCourseListing, ListedCourse } from '@/composables/useCourseListing'

// 1. 类型定义
type Course = ListedCourse

interface Volunteer {
  course: Course
  rank: number
}

const { courses: availableCourses, loading: courseLoading, reloadTables } = useCourseListing()

// 3. 状态管理
const courseTypeFilter = ref<string | null>(null) // 筛选条件
const selectedVolunteers = ref<Volunteer[]>([]) // 已选志愿
const loading = ref(false)
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')
const confirmDialog = ref(false)
const confirmDialogTitle = ref('')
const confirmDialogText = ref('')
const confirmAction = ref<() => void>(() => {})

// 4. 计算属性：课程筛选
const filteredCourses = computed(() => {
  const data = availableCourses.value
  if (!courseTypeFilter.value) return data
  return data.filter(c => c.type === courseTypeFilter.value)
})

// 5. 核心逻辑

const showMessage = (msg: string, color: string = 'success') => {
  snackbarText.value = msg
  snackbarColor.value = color
  snackbar.value = true
}

const showConfirm = (title: string, text: string, action: () => void, confirmText: string = '确定') => {
  confirmDialogTitle.value = title
  confirmDialogText.value = text
  confirmAction.value = action
  confirmDialog.value = true
}

const handleConfirm = () => {
  confirmAction.value()
  confirmDialog.value = false
}

// 加入志愿（含冲突检测）
const handleAddVolunteer = (course: Course) => {
  // 检查是否已添加
  if (selectedVolunteers.value.some(v => v.course.id === course.id)) {
    showMessage('该课程已在志愿列表中', 'warning')
    return
  }
  
  // 检查名额
  if (course.remain <= 0) {
    showMessage('该课程名额已满', 'error')
    return
  }
  
  // 检查数量限制
  if (selectedVolunteers.value.length >= 5) {
    showMessage('最多只能选择5个志愿', 'warning')
    return
  }

  // 冲突检测
  const conflict = selectedVolunteers.value.find(v => v.course.time === course.time)
  if (conflict) {
    showConfirm(
      '选课冲突提示',
      `检测到时间冲突：${course.name} 与已选的 ${conflict.course.name} 均为 ${course.time}。是否仍要添加？`,
      () => addToVolunteers(course),
      '坚持添加'
    )
  } else {
    addToVolunteers(course)
  }
}

const addToVolunteers = (course: Course) => {
  selectedVolunteers.value.push({
    course,
    rank: selectedVolunteers.value.length + 1
  })
  showMessage('添加成功，请确认志愿优先级')
}

// 移除志愿
const handleRemoveVolunteer = (index: number) => {
  selectedVolunteers.value.splice(index, 1)
  // 重新排序
  selectedVolunteers.value.forEach((v, idx) => {
    v.rank = idx + 1
  })
}

// 提交志愿
const handleSubmit = () => {
  if (selectedVolunteers.value.length === 0) {
    showMessage('请至少选择一门课程', 'warning')
    return
  }
  
  showConfirm('提交确认', '确定要提交当前选课志愿吗？提交后不可修改。', () => {
    loading.value = true
    setTimeout(() => {
      loading.value = false
      showMessage('选课志愿提交成功！')
      reloadTables(true)
    }, 1000)
  })
}

// 拖拽排序简单的模拟实现
const moveVolunteer = (index: number, direction: 'up' | 'down') => {
  if (direction === 'up' && index > 0) {
    const temp = selectedVolunteers.value[index]
    selectedVolunteers.value[index] = selectedVolunteers.value[index - 1]
    selectedVolunteers.value[index - 1] = temp
  } else if (direction === 'down' && index < selectedVolunteers.value.length - 1) {
    const temp = selectedVolunteers.value[index]
    selectedVolunteers.value[index] = selectedVolunteers.value[index + 1]
    selectedVolunteers.value[index + 1] = temp
  }
  // 更新 rank
  selectedVolunteers.value.forEach((v, idx) => {
    v.rank = idx + 1
  })
}

// Headers for course table
const headers: any[] = [
  { title: '课程名称', key: 'name', align: 'start' },
  { title: '任课教师', key: 'teacher', align: 'start' },
  { title: '学分', key: 'credit', align: 'center' },
  { title: '上课时间', key: 'time', align: 'start' },
  { title: '剩余名额', key: 'remain', align: 'center' },
  { title: '操作', key: 'actions', align: 'center', sortable: false },
]
</script>

<template>
  <v-container fluid class="pa-4 h-100 d-flex flex-column">
    <!-- 顶部提示 -->
    <v-alert
      color="error"
      variant="tonal"
      icon="mdi-alert-circle"
      border="start"
      class="mb-4 flex-shrink-0"
      density="compact"
    >
      当前阶段：第二轮补选（2025-12-05 至 2025-12-10）
    </v-alert>
    
    <div class="d-flex flex-grow-1 gap-4 flex-column flex-md-row" style="overflow: hidden;">
      <!-- 左侧筛选与操作 -->
      <div class="left-panel d-flex flex-column gap-4" style="min-width: 300px; max-width: 100%; overflow: hidden;">
        <v-card elevation="1">
          <v-card-title class="text-subtitle-1 font-weight-bold">课程筛选</v-card-title>
          <v-card-text>
            <v-select
              v-model="courseTypeFilter"
              :items="[
                { title: '全部课程类型', value: null },
                { title: '专业必修课', value: 'compulsory' },
                { title: '通识选修课', value: 'elective' }
              ]"
              item-title="title"
              item-value="value"
              label="选择课程类型"
              variant="outlined"
              density="compact"
              hide-details
            ></v-select>
            
            <div class="mt-4">
              <div class="text-body-2 text-medium-emphasis mb-2">已选志愿：{{ selectedVolunteers.length }} / 5</div>
              <v-btn
                color="primary"
                block
                :loading="loading"
                :disabled="selectedVolunteers.length === 0"
                @click="handleSubmit"
              >
                提交所有志愿
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
        
        <!-- 志愿列表 -->
        <v-card elevation="1" class="flex-grow-1 d-flex flex-column" style="overflow: hidden;">
          <v-card-title class="text-subtitle-1 font-weight-bold bg-grey-lighten-4">
            已选志愿 (优先级排序)
          </v-card-title>
          <v-card-text class="flex-grow-1 overflow-y-auto pa-2">
            <div v-if="selectedVolunteers.length === 0" class="text-center text-grey pa-4">
              暂无志愿
            </div>
            <div v-else class="d-flex flex-column gap-2">
              <v-card
                v-for="(item, index) in selectedVolunteers"
                :key="item.course.id"
                variant="outlined"
                class="pa-2"
              >
                <div class="d-flex align-center">
                  <v-avatar color="primary" size="24" class="mr-3 text-caption font-weight-bold">
                    {{ item.rank }}
                  </v-avatar>
                  <div class="flex-grow-1">
                    <div class="font-weight-bold text-body-2">{{ item.course.name }}</div>
                    <div class="text-caption text-grey">{{ item.course.time }}</div>
                  </div>
                  <div class="d-flex gap-1">
                    <v-btn icon size="x-small" variant="text" :disabled="index === 0" @click="moveVolunteer(index, 'up')">
                      <v-icon>mdi-arrow-up</v-icon>
                    </v-btn>
                    <v-btn icon size="x-small" variant="text" :disabled="index === selectedVolunteers.length - 1" @click="moveVolunteer(index, 'down')">
                      <v-icon>mdi-arrow-down</v-icon>
                    </v-btn>
                    <v-btn icon size="x-small" variant="text" color="error" @click="handleRemoveVolunteer(index)">
                      <v-icon>mdi-close</v-icon>
                    </v-btn>
                  </div>
                </div>
              </v-card>
            </div>
          </v-card-text>
        </v-card>
      </div>
      
      <!-- 右侧课程列表 -->
      <v-card class="flex-grow-1 d-flex flex-column" elevation="1" style="overflow: hidden;">
        <v-data-table
          :headers="headers"
          :items="filteredCourses"
          class="flex-grow-1 overflow-y-auto"
          fixed-header
          :loading="courseLoading"
          items-per-page="10"
        >
          <template v-slot:item.name="{ item }">
            <span class="font-weight-bold mr-2">{{ item.name }}</span>
            <v-chip
              size="x-small"
              :color="item.type === 'compulsory' ? 'error' : 'success'"
              label
            >
              {{ item.type === 'compulsory' ? '必修' : '选修' }}
            </v-chip>
          </template>
          
          <template v-slot:item.remain="{ item }">
            <span :class="{'text-error font-weight-bold': item.remain < 10}">
              {{ item.remain }}
            </span>
          </template>
          
          <template v-slot:item.actions="{ item }">
            <v-btn
              size="small"
              :color="item.remain <= 0 ? 'grey' : 'primary'"
              :disabled="item.remain <= 0"
              @click="handleAddVolunteer(item)"
              variant="flat"
            >
              {{ item.remain <= 0 ? '名额已满' : '加入志愿' }}
            </v-btn>
          </template>
        </v-data-table>
      </v-card>
    </div>

    <!-- Confirmation Dialog -->
    <v-dialog v-model="confirmDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h5">{{ confirmDialogTitle }}</v-card-title>
        <v-card-text>{{ confirmDialogText }}</v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey-darken-1" variant="text" @click="confirmDialog = false">取消</v-btn>
          <v-btn color="primary" variant="text" @click="handleConfirm">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar -->
    <v-snackbar
      v-model="snackbar"
      :color="snackbarColor"
      timeout="3000"
      location="top"
    >
      {{ snackbarText }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<style scoped>
.gap-4 {
  gap: 16px;
}
.gap-2 {
  gap: 8px;
}
.gap-1 {
  gap: 4px;
}
.h-100 {
  height: 100% !important;
}
.flex-grow-1 {
  flex-grow: 1 !important;
}
.flex-shrink-0 {
  flex-shrink: 0 !important;
}
/* Fix data table height */
:deep(.v-data-table) {
  height: 100%;
  display: flex;
  flex-direction: column;
}
:deep(.v-data-table__wrapper) {
  flex-grow: 1;
}
</style>
