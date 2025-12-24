<script setup lang="ts">
/**
 * 考试证书链接 (Material Design 适配版)
 * 
 * Material Design 适配说明：
 * 1. 采用左侧主内容、右侧侧边栏的经典布局
 * 2. 链接卡片使用 v-card，支持 hover 浮起效果 (elevation)
 * 3. 收藏功能使用 mdi-star 图标，点击有动态反馈
 * 4. 热门推荐列表使用简洁的 v-list 样式
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { io, Socket } from 'socket.io-client'

// --- 类型定义 ---
interface LinkItem {
  id: number
  name: string
  url: string
  description: string
  icon?: string
  category: string
  is_official: boolean
  click_count: number
  is_collected: boolean
}

const searchKeyword = ref('')
const currentCategory = ref('all')
const links = ref<LinkItem[]>([])
const loading = ref(false)
const snackbar = ref({ show: false, text: '', color: 'success' })

const categories = [
  { key: 'all', label: '全部', icon: 'mdi-apps' },
  { key: '计算机类', label: '计算机类', icon: 'mdi-monitor' },
  { key: '英语类', label: '英语类', icon: 'mdi-book-alphabet' },
  { key: '职业资格类', label: '职业资格类', icon: 'mdi-card-account-details' },
  { key: '专业证书类', label: '专业证书类', icon: 'mdi-medal' },
  { key: '其他', label: '其他', icon: 'mdi-dots-horizontal' }
]

const filteredLinks = computed(() => {
  let res = links.value
  if (currentCategory.value !== 'all') {
    res = res.filter(l => l.category === currentCategory.value)
  }
  if (searchKeyword.value) {
    res = res.filter(l => l.name.includes(searchKeyword.value))
  }
  return res
})

const hotLinks = computed(() => {
  return [...links.value].sort((a, b) => b.click_count - a.click_count).slice(0, 5)
})

const fetchLinks = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (currentCategory.value !== 'all') params.category = currentCategory.value
    if (searchKeyword.value) params.keyword = searchKeyword.value

    const response = await axios.get('/cert/list', {
      params,
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    links.value = response.data
  } catch (error) {
    // Mock data
    links.value = [
      { id: 1, name: '全国计算机等级考试', url: 'https://ncre.neea.edu.cn/', description: 'NCRE 官方报名与成绩查询网站', category: '计算机类', is_official: true, click_count: 1200, is_collected: false, icon: 'mdi-laptop' },
      { id: 2, name: 'CET-4/6 报名', url: 'https://cet.neea.edu.cn/', description: '全国大学英语四六级考试报名', category: '英语类', is_official: true, click_count: 2500, is_collected: true, icon: 'mdi-translate' },
      { id: 3, name: '教师资格证', url: 'https://ntce.neea.edu.cn/', description: '中小学教师资格考试网', category: '职业资格类', is_official: true, click_count: 800, is_collected: false, icon: 'mdi-school' }
    ]
  } finally {
    loading.value = false
  }
}

const openLink = async (link: LinkItem) => {
  window.open(link.url, '_blank')
  try {
    await axios.post(`/cert/click/${link.id}`)
    link.click_count++
  } catch (e) {
    // Ignore
  }
}

const toggleCollect = async (link: LinkItem, e: Event) => {
  e.stopPropagation() // Prevent card click
  try {
    // const response = await axios.post(...)
    // Mock toggle
    link.is_collected = !link.is_collected
    showSnackbar(link.is_collected ? '收藏成功' : '已取消收藏', 'success')
  } catch (error) {
    showSnackbar('操作失败', 'error')
  }
}

const showSnackbar = (text: string, color: string) => {
  snackbar.value = { show: true, text, color }
}

onMounted(() => {
  fetchLinks()
  initRealtime()
  window.addEventListener('storage', handleStorageSync)
})
onUnmounted(() => {
  socket?.disconnect()
  window.removeEventListener('storage', handleStorageSync)
})

let socket: Socket | null = null
const initRealtime = () => {
  const host = window.location.hostname
  socket = io('/', { transports: ['websocket', 'polling'] })
  socket.on('cert_links_updated', () => {
    fetchLinks()
  })
}
const handleStorageSync = (e: StorageEvent) => {
  if (e.key === 'cert_links_version') {
    fetchLinks()
  }
}
</script>

<template>
  <v-container fluid class="pa-4">
    <!-- 头部搜索 -->
    <v-card class="mb-6 pa-6 bg-grey-lighten-5" elevation="0" border>
      <div class="d-flex flex-column flex-md-row align-center">
        <div class="flex-grow-1 mb-4 mb-md-0">
          <h2 class="text-h5 font-weight-bold text-grey-darken-3">考试证书链接</h2>
          <div class="text-body-2 text-grey">一站式考试报名与证书查询入口</div>
        </div>
        
        <v-text-field
          v-model="searchKeyword"
          placeholder="搜索考试或证书名称..."
          variant="solo"
          prepend-inner-icon="mdi-magnify"
          density="comfortable"
          hide-details
          class="search-input"
          rounded="lg"
          elevation="2"
        ></v-text-field>
        
        <v-btn
          color="amber-darken-2"
          variant="tonal"
          prepend-icon="mdi-star"
          class="ml-4"
          height="48"
        >
          我的收藏
        </v-btn>
      </div>
    </v-card>

    <v-row>
      <!-- 左侧内容区 -->
      <v-col cols="12" md="9">
        <!-- 分类导航 -->
        <v-sheet class="mb-6">
          <v-chip-group
            v-model="currentCategory"
            selected-class="text-primary"
            mandatory
          >
            <v-chip
              v-for="cat in categories"
              :key="cat.key"
              :value="cat.key"
              variant="outlined"
              filter
            >
              <v-icon start size="small">{{ cat.icon }}</v-icon>
              {{ cat.label }}
            </v-chip>
          </v-chip-group>
        </v-sheet>

        <!-- 链接列表 -->
        <v-row>
          <v-col
            v-for="link in filteredLinks"
            :key="link.id"
            cols="12"
            sm="6"
            lg="4"
          >
            <v-hover v-slot="{ isHovering, props }">
              <v-card
                v-bind="props"
                :elevation="isHovering ? 6 : 2"
                class="h-100 cursor-pointer transition-swing d-flex flex-column"
                @click="openLink(link)"
              >
                <div class="d-flex align-start pa-4">
                  <v-avatar color="green-lighten-5" rounded size="48" class="mr-3">
                    <v-icon color="green" size="28">{{ link.icon || 'mdi-link' }}</v-icon>
                  </v-avatar>
                  <div class="flex-grow-1 overflow-hidden">
                    <div class="d-flex align-center mb-1">
                      <div class="text-subtitle-1 font-weight-bold text-truncate mr-2">{{ link.name }}</div>
                      <v-chip v-if="link.is_official" color="success" size="x-small" label>官方</v-chip>
                    </div>
                    <div class="text-caption text-grey text-truncate-2">{{ link.description || '暂无描述' }}</div>
                  </div>
                  <v-btn
                    icon
                    variant="text"
                    density="comfortable"
                    :color="link.is_collected ? 'amber' : 'grey-lighten-1'"
                    @click="toggleCollect(link, $event)"
                  >
                    <v-icon>{{ link.is_collected ? 'mdi-star' : 'mdi-star-outline' }}</v-icon>
                  </v-btn>
                </div>
                
                <v-spacer></v-spacer>
                
                <v-divider></v-divider>
                
                <div class="px-4 py-2 d-flex justify-space-between align-center text-caption text-grey">
                  <span>{{ link.category }}</span>
                  <div class="d-flex align-center">
                    <v-icon size="small" class="mr-1">mdi-eye-outline</v-icon>
                    {{ link.click_count }}
                  </div>
                </div>
              </v-card>
            </v-hover>
          </v-col>
        </v-row>
        
        <v-sheet v-if="filteredLinks.length === 0" class="d-flex flex-column align-center justify-center py-12">
          <v-icon size="64" color="grey-lighten-2">mdi-link-variant-off</v-icon>
          <div class="text-body-1 text-grey mt-2">暂无相关链接</div>
        </v-sheet>
      </v-col>

      <!-- 右侧侧边栏 -->
      <v-col cols="12" md="3">
        <!-- 热门推荐 -->
        <v-card class="mb-4" elevation="2">
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon color="error" class="mr-2">mdi-trophy-outline</v-icon>
            热门推荐
          </v-card-title>
          <v-divider></v-divider>
          <v-list density="compact">
            <v-list-item
              v-for="(link, index) in hotLinks"
              :key="link.id"
              :value="link"
              @click="openLink(link)"
              rounded
              class="mb-1"
            >
              <template v-slot:prepend>
                <v-avatar
                  size="24"
                  :color="index < 3 ? 'red-lighten-4' : 'grey-lighten-3'"
                  class="mr-2"
                >
                  <span :class="index < 3 ? 'text-red font-weight-bold' : 'text-grey'" style="font-size: 12px">
                    {{ index + 1 }}
                  </span>
                </v-avatar>
              </template>
              <v-list-item-title class="text-body-2">{{ link.name }}</v-list-item-title>
              <template v-slot:append>
                <v-icon color="error" size="small">mdi-fire</v-icon>
              </template>
            </v-list-item>
          </v-list>
        </v-card>

        <!-- 使用说明 -->
        <v-card color="blue-grey-lighten-5" elevation="0" border>
          <v-card-title class="text-subtitle-2 font-weight-bold d-flex align-center">
            <v-icon size="small" class="mr-2">mdi-information-outline</v-icon>
            使用说明
          </v-card-title>
          <v-card-text class="text-caption text-grey-darken-2 pt-0">
            <p class="mb-1">1. 点击卡片可直接跳转至官方网站（新窗口打开）。</p>
            <p class="mb-1">2. 点击右上角星号 <v-icon size="small" icon="mdi-star"></v-icon> 可收藏常用链接。</p>
            <p class="mb-0">3. 如发现链接失效，请联系管理员反馈。</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="2000">
      {{ snackbar.text }}
    </v-snackbar>
  </v-container>
</template>

<style scoped>
.search-input {
  max-width: 400px;
  width: 100%;
}
.text-truncate-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.transition-swing {
  transition: 0.3s cubic-bezier(0.25, 0.8, 0.5, 1);
}
</style>
