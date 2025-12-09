<script setup lang="ts">
/**
 * 办事大厅 (Material Design 适配版)
 * 
 * Material Design 适配说明：
 * 1. 顶部大卡片展示标题和搜索，使用 elevation 营造层级
 * 2. 使用 v-chip-group 实现分类筛选，交互流畅
 * 3. 使用 v-card + v-hover 实现服务卡片，hover 时 elevation 提升
 * 4. 状态指示使用 v-badge 或颜色圆点
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const searchKeyword = ref('')
const currentCategory = ref('all')
const services = ref<any[]>([])
const quickLinks = ref<any[]>([])
const loading = ref(false)

const snackbar = reactive({
  show: false,
  text: '',
  color: 'error'
})

const showMessage = (text: string, color: 'success' | 'error' | 'warning' = 'error') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

const categories = [
  { key: 'all', label: '全部服务', icon: 'mdi-apps' },
  { key: '学籍管理', label: '学籍管理', icon: 'mdi-account-school' },
  { key: '课程管理', label: '课程管理', icon: 'mdi-book-open-variant' },
  { key: '成绩管理', label: '成绩管理', icon: 'mdi-chart-line' },
  { key: '证书办理', label: '证书办理', icon: 'mdi-certificate' },
  { key: '其他服务', label: '其他服务', icon: 'mdi-dots-horizontal' }
]

const filteredServices = computed(() => {
  return services.value.filter(item => {
    const matchCategory = currentCategory.value === 'all' || item.category === currentCategory.value
    const matchKeyword = !searchKeyword.value || item.name.includes(searchKeyword.value)
    return matchCategory && matchKeyword
  })
})

const fetchQuickLinks = async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/quick-link/list', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    quickLinks.value = response.data
  } catch (error) {
    showMessage('获取快捷入口失败', 'error')
    // Fallback mock
    quickLinks.value = [
        { id: 1, name: '我的课表', description: '查看本学期课程安排', icon: 'mdi-calendar-clock', icon_bg: '#E3F2FD', icon_color: '#1976D2', route: '/material/dashboard' },
        { id: 2, name: '成绩查询', description: '查询历年考试成绩', icon: 'mdi-chart-bar', icon_bg: '#E8F5E9', icon_color: '#388E3C', route: '/material/dashboard' }
    ]
  }
}

const fetchServices = async () => {
  loading.value = true
  try {
    const response = await axios.get('http://localhost:8000/api/service/list', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    services.value = response.data
  } catch (error) {
    // Mock data
    services.value = [
      { id: 1, name: '缓考申请', category: '课程管理', processing_time: '3个工作日', status: 'available', icon: 'mdi-timer-sand' },
      { id: 2, name: '休学申请', category: '学籍管理', processing_time: '5个工作日', status: 'available', icon: 'mdi-account-off' },
      { id: 3, name: '成绩复核', category: '成绩管理', processing_time: '3个工作日', status: 'paused', icon: 'mdi-file-search' },
      { id: 4, name: '在读证明', category: '证书办理', processing_time: '即时', status: 'available', icon: 'mdi-file-certificate' }
    ]
  } finally {
    loading.value = false
  }
}

const handleServiceClick = (item: any) => {
  // router.push(`/service/detail/${item.id}`)
  // For Material demo, maybe show a dialog or navigate
  // console.log('Service clicked:', item)
}

const getCategoryIcon = (catKey: string) => {
  return categories.find(c => c.key === catKey)?.icon || 'mdi-circle-small'
}

const getStatusColor = (status: string) => {
  return status === 'available' ? 'success' : 'grey'
}

const getStatusText = (status: string) => {
  return status === 'available' ? '可办理' : '暂停办理'
}

onMounted(() => {
  fetchServices()
  fetchQuickLinks()
})
</script>

<template>
  <v-container fluid class="pa-4">
    <!-- 头部区域 -->
    <v-card class="mb-6 pa-6" elevation="2" rounded="lg">
      <div class="d-flex flex-column flex-md-row justify-space-between align-center">
        <div class="mb-4 mb-md-0">
          <h2 class="text-h4 font-weight-bold text-primary mb-1">办事大厅</h2>
          <div class="text-subtitle-1 text-grey">一站式教务服务平台</div>
        </div>
        
        <div class="d-flex align-center" style="width: 100%; max-width: 500px;">
          <v-text-field
            v-model="searchKeyword"
            label="搜索办事项目..."
            variant="outlined"
            prepend-inner-icon="mdi-magnify"
            density="comfortable"
            hide-details
            class="mr-4 flex-grow-1"
            rounded="pill"
          ></v-text-field>
          
          <v-btn
            color="secondary"
            prepend-icon="mdi-file-document-outline"
            variant="tonal"
            height="48"
            rounded="pill"
          >
            我的申请
          </v-btn>
        </div>
      </div>
    </v-card>

    <!-- 快捷入口 -->
    <div class="mb-6">
      <h3 class="text-h6 font-weight-bold mb-4 d-flex align-center">
        <v-icon color="primary" class="mr-2">mdi-rocket-launch</v-icon>
        快捷入口
      </h3>
      <v-row>
        <v-col v-for="link in quickLinks" :key="link.id" cols="12" sm="6" md="3">
          <v-hover v-slot="{ isHovering, props }">
            <v-card
              v-bind="props"
              :elevation="isHovering ? 6 : 1"
              class="cursor-pointer transition-swing"
              @click="router.push(link.route)"
            >
              <v-card-item>
                <template v-slot:prepend>
                  <v-avatar
                    :color="link.icon_bg"
                    size="48"
                    rounded="lg"
                  >
                    <v-icon :color="link.icon_color" size="24">{{ link.icon }}</v-icon>
                  </v-avatar>
                </template>
                <v-card-title class="text-body-1 font-weight-bold">{{ link.name }}</v-card-title>
                <v-card-subtitle class="text-caption">{{ link.description }}</v-card-subtitle>
              </v-card-item>
            </v-card>
          </v-hover>
        </v-col>
      </v-row>
    </div>

    <!-- 服务分类 -->
    <v-sheet class="mb-6 bg-transparent">
      <v-chip-group
        v-model="currentCategory"
        selected-class="text-primary"
        mandatory
        filter
      >
        <v-chip
          v-for="cat in categories"
          :key="cat.key"
          :value="cat.key"
          filter-icon="mdi-check"
          variant="elevated"
          elevation="1"
          class="mr-2"
        >
          <v-icon start size="small">{{ cat.icon }}</v-icon>
          {{ cat.label }}
        </v-chip>
      </v-chip-group>
    </v-sheet>

    <!-- 服务列表 -->
    <v-row>
      <v-col
        v-for="item in filteredServices"
        :key="item.id"
        cols="12"
        sm="6"
        md="4"
        lg="3"
      >
        <v-hover v-slot="{ isHovering, props }">
          <v-card
            v-bind="props"
            :elevation="isHovering ? 8 : 2"
            class="cursor-pointer h-100 d-flex flex-column"
            @click="handleServiceClick(item)"
          >
            <v-card-item>
              <template v-slot:prepend>
                <v-avatar color="blue-lighten-5" size="48" rounded="lg">
                  <v-icon color="primary" size="28">{{ item.icon || 'mdi-file-document' }}</v-icon>
                </v-avatar>
              </template>
              <v-card-title class="text-h6 font-weight-bold mb-1">{{ item.name }}</v-card-title>
              <v-card-subtitle>
                <v-chip size="x-small" label class="mr-2">{{ item.category }}</v-chip>
                <span class="text-caption text-grey">
                  <v-icon size="small" class="mr-1">mdi-clock-outline</v-icon>
                  {{ item.processing_time }}
                </span>
              </v-card-subtitle>
            </v-card-item>

            <v-spacer></v-spacer>

            <v-card-actions class="px-4 pb-4 pt-0">
              <div class="d-flex align-center">
                <v-icon :color="getStatusColor(item.status)" size="small" class="mr-1">mdi-circle</v-icon>
                <span :class="`text-caption text-${getStatusColor(item.status)}`">
                  {{ getStatusText(item.status) }}
                </span>
              </div>
              <v-spacer></v-spacer>
              <v-btn
                variant="text"
                color="primary"
                size="small"
                append-icon="mdi-arrow-right"
              >
                办理
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-hover>
      </v-col>
    </v-row>

    <v-sheet v-if="filteredServices.length === 0 && !loading" class="d-flex flex-column align-center justify-center py-12 bg-transparent">
      <v-icon size="64" color="grey-lighten-1">mdi-file-search-outline</v-icon>
      <div class="text-h6 text-grey mt-4">暂无相关办事项目</div>
    </v-sheet>
  </v-container>
  
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
</template>

<style scoped>
.transition-swing {
  transition: 0.3s cubic-bezier(0.25, 0.8, 0.5, 1);
}
</style>
