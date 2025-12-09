<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import axios from 'axios'
import { useTheme } from 'vuetify'

const theme = useTheme()
const search = ref('')
const activeTab = ref(0) // 0: Pending, 1: Approved, 2: All
const leaves = ref<any[]>([])
const loading = ref(false)
const selected = ref<any[]>([])
const dialog = ref(false)
const currentLeave = ref<any>(null)
const approvalComment = ref('')
const approving = ref(false)
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

// Table Headers
const headers = [
  { title: '学生姓名', key: 'student_name', align: 'start', sortable: true },
  { title: '课程', key: 'course_name', sortable: true },
  { title: '请假类型', key: 'type', sortable: true },
  { title: '提交时间', key: 'created_at', sortable: true },
  { title: '状态', key: 'status', sortable: true },
  { title: '操作', key: 'actions', sortable: false, align: 'end' },
]

// Fetch Leaves
const fetchLeaves = async () => {
  loading.value = true
  try {
    const statusParam = activeTab.value === 0 ? 'pending' : activeTab.value === 1 ? 'approved' : undefined
    const response = await axios.get('http://localhost:8000/api/leave/teacher/list', {
      params: statusParam ? { status: statusParam } : {},
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    leaves.value = response.data
  } catch (error) {
    showSnackbar('获取请假列表失败', 'error')
  } finally {
    loading.value = false
  }
}

// Watch tab change to refetch
watch(activeTab, () => {
  fetchLeaves()
})

const openApproveDialog = (item: any) => {
  currentLeave.value = item
  approvalComment.value = ''
  dialog.value = true
}

const approveLeave = async (status: 'approved' | 'rejected') => {
  if (!currentLeave.value) return
  
  approving.value = true
  try {
    await axios.post('http://localhost:8000/api/leave/approve', {
      leave_id: currentLeave.value.id,
      result: status,
      opinion: approvalComment.value
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })

    // Update local state
    const index = leaves.value.findIndex(l => l.id === currentLeave.value.id)
    if (index !== -1) {
      leaves.value[index].status = status
    }
    
    showSnackbar(status === 'approved' ? '已通过审批' : '已拒绝申请', status === 'approved' ? 'success' : 'error')
    dialog.value = false
  } catch (error) {
    showSnackbar('操作失败', 'error')
  } finally {
    approving.value = false
  }
}

const showSnackbar = (text: string, color: string) => {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

const getTypeColor = (type: string) => {
  switch(type) {
    case 'sick': return 'red-lighten-1'
    case 'personal': return 'orange-lighten-1'
    default: return 'blue-lighten-1'
  }
}

const getTypeIcon = (type: string) => {
  switch(type) {
    case 'sick': return 'mdi-hospital'
    case 'personal': return 'mdi-home'
    default: return 'mdi-help-circle'
  }
}

const getStatusColor = (status: string) => {
  switch(status) {
    case 'approved': return 'success'
    case 'rejected': return 'error'
    case 'pending': return 'warning'
    default: return 'grey'
  }
}

const exportData = () => {
  // Implement export logic
  window.open('/api/leaves/export', '_blank')
}

onMounted(() => {
  fetchLeaves()
})
</script>

<template>
  <v-container fluid class="fill-height align-start pa-6">
    <v-card class="w-100 rounded-xl" elevation="1">
      <!-- Toolbar -->
      <v-toolbar color="surface" density="comfortable" class="border-b pr-4">
        <v-tabs v-model="activeTab" color="primary" class="ml-4">
          <v-tab :value="0" class="text-body-1"><v-icon start>mdi-clock-outline</v-icon>待审批</v-tab>
          <v-tab :value="1" class="text-body-1"><v-icon start>mdi-check-circle-outline</v-icon>已审批</v-tab>
          <v-tab :value="2" class="text-body-1"><v-icon start>mdi-file-document-multiple-outline</v-icon>全部</v-tab>
        </v-tabs>
        
        <v-spacer></v-spacer>
        
        <div style="width: 300px">
          <v-text-field
            v-model="search"
            density="compact"
            variant="outlined"
            label="搜索学生姓名/课程"
            prepend-inner-icon="mdi-magnify"
            hide-details
            single-line
            rounded="pill"
          ></v-text-field>
        </div>
        
        <v-btn variant="outlined" class="ml-4" prepend-icon="mdi-download" @click="exportData">
          导出 Excel
        </v-btn>
      </v-toolbar>

      <!-- Data Table -->
      <v-data-table
        v-model="selected"
        :headers="headers"
        :items="leaves"
        :search="search"
        :loading="loading"
        show-select
        hover
        density="comfortable"
        class="elevation-0"
      >
        <!-- Custom Columns -->
        <template v-slot:item.student_name="{ item }">
          <div class="d-flex align-center py-2">
            <v-avatar size="32" class="mr-3" color="primary-lighten-4">
              <v-img v-if="item.student_avatar" :src="item.student_avatar"></v-img>
              <span v-else class="text-primary font-weight-bold">{{ item.student_name.charAt(0) }}</span>
            </v-avatar>
            <span class="font-weight-medium">{{ item.student_name }}</span>
          </div>
        </template>

        <template v-slot:item.type="{ item }">
          <v-chip
            size="small"
            :color="getTypeColor(item.type)"
            variant="flat"
            class="text-white"
          >
            <v-icon start size="small">{{ getTypeIcon(item.type) }}</v-icon>
            {{ item.type === 'sick' ? '病假' : item.type === 'personal' ? '事假' : '其他' }}
          </v-chip>
        </template>

        <template v-slot:item.status="{ item }">
          <v-badge
            :color="getStatusColor(item.status)"
            dot
            inline
            class="mr-2"
          ></v-badge>
          <span :class="`text-${getStatusColor(item.status)}`">
            {{ item.status === 'approved' ? '已通过' : item.status === 'rejected' ? '已拒绝' : '待审批' }}
          </span>
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn
            variant="text"
            color="primary"
            size="small"
            @click="openApproveDialog(item)"
          >
            详情 / 审批
          </v-btn>
        </template>
      </v-data-table>
    </v-card>

    <!-- Approval Dialog -->
    <v-dialog v-model="dialog" max-width="800" transition="dialog-bottom-transition">
      <v-card class="rounded-lg" elevation="4" v-if="currentLeave">
        <v-toolbar color="primary" density="compact">
          <v-toolbar-title>请假详情审批</v-toolbar-title>
          <v-btn icon @click="dialog = false"><v-icon>mdi-close</v-icon></v-btn>
        </v-toolbar>

        <v-card-text class="pa-6">
          <v-row>
            <v-col cols="12" md="7">
              <div class="text-h6 mb-4 d-flex align-center">
                <v-avatar color="primary" size="40" class="mr-3">
                  <span class="text-white">{{ currentLeave.student_name.charAt(0) }}</span>
                </v-avatar>
                <div>
                  <div>{{ currentLeave.student_name }}</div>
                  <div class="text-caption text-grey">提交于 {{ currentLeave.created_at }}</div>
                </div>
              </div>

              <v-list density="compact" class="bg-grey-lighten-5 rounded-lg pa-2 mb-4">
                <v-list-item prepend-icon="mdi-book-open-variant" title="课程" :subtitle="currentLeave.course_name"></v-list-item>
                <v-list-item prepend-icon="mdi-calendar-range" title="时间" :subtitle="`${currentLeave.start_date} 至 ${currentLeave.end_date}`"></v-list-item>
                <v-list-item prepend-icon="mdi-format-list-bulleted-type" title="类型" :subtitle="currentLeave.type"></v-list-item>
              </v-list>

              <div class="text-subtitle-1 font-weight-bold mb-2">请假理由</div>
              <p class="text-body-2 mb-4">{{ currentLeave.reason }}</p>

              <div class="text-subtitle-1 font-weight-bold mb-2">审批意见</div>
              <v-textarea
                v-model="approvalComment"
                variant="outlined"
                placeholder="请输入审批意见..."
                rows="3"
                auto-grow
              ></v-textarea>
            </v-col>

            <v-col cols="12" md="5" class="border-s">
              <div class="text-subtitle-1 font-weight-bold mb-3">证明材料</div>
              <v-img
                v-if="currentLeave.attachment"
                :src="currentLeave.attachment"
                cover
                class="rounded-lg bg-grey-lighten-3"
                aspect-ratio="1"
              >
                <template v-slot:placeholder>
                  <div class="d-flex align-center justify-center fill-height">
                    <v-progress-circular indeterminate color="grey-lighten-5"></v-progress-circular>
                  </div>
                </template>
              </v-img>
              <div v-else class="d-flex align-center justify-center bg-grey-lighten-4 rounded-lg" style="height: 200px">
                <div class="text-grey text-center">
                  <v-icon size="40" class="mb-2">mdi-attachment-off</v-icon>
                  <div>无证明材料</div>
                </div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions class="pa-4 bg-grey-lighten-5">
          <v-spacer></v-spacer>
          <v-btn
            color="error"
            variant="tonal"
            prepend-icon="mdi-close"
            @click="approveLeave('rejected')"
            :loading="approving"
            class="mr-2"
          >
            拒绝
          </v-btn>
          <v-btn
            color="success"
            variant="elevated"
            prepend-icon="mdi-check"
            @click="approveLeave('approved')"
            :loading="approving"
          >
            通过
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar -->
    <v-snackbar
      v-model="snackbar"
      :color="snackbarColor"
      location="top right"
      timeout="3000"
    >
      {{ snackbarText }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>
