<template>
  <div class="service-hall">
    <!-- 顶部搜索区 -->
    <div class="header-section">
      <div class="title-area">
        <h2>办事大厅</h2>
        <p class="subtitle">一站式教务服务平台</p>
      </div>
      <div class="search-area">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索办事项目..."
          class="search-input"
          :prefix-icon="Search"
          clearable
        />
        <el-button type="primary" @click="handleMyApplications">我的申请</el-button>
      </div>
    </div>

    <!-- 分类导航 -->
    <div class="category-nav">
      <div
        v-for="cat in categories"
        :key="cat.key"
        class="category-item"
        :class="{ active: currentCategory === cat.key }"
        @click="currentCategory = cat.key"
      >
        <el-icon class="cat-icon"><component :is="cat.icon" /></el-icon>
        <span>{{ cat.label }}</span>
      </div>
    </div>

    <!-- 快捷入口 -->
    <div class="quick-links" v-if="displayQuickLinks.length">
      <div 
        v-for="link in displayQuickLinks" 
        :key="link.id" 
        class="quick-link-card" 
        @click="router.push(link.route)"
      >
        <el-icon class="quick-icon" :style="{ background: link.icon_bg, color: link.icon_color }">
          <component :is="link.icon" />
        </el-icon>
        <div class="quick-info">
          <h4>{{ link.name }}</h4>
          <p>{{ link.description }}</p>
        </div>
      </div>
    </div>

    <!-- 办事项目列表 -->
    <div class="service-list">
      <el-row :gutter="20">
        <el-col
          v-for="item in filteredServices"
          :key="item.id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <div class="service-card" @click="handleServiceClick(item)">
            <div class="card-icon">
              <el-icon><component :is="item.icon || 'Document'" /></el-icon>
            </div>
            <div class="card-content">
              <h3>{{ item.name }}</h3>
              <div class="tags">
                <el-tag size="small" effect="plain">{{ getCategoryLabel(item.category) }}</el-tag>
                <el-tag size="small" type="info" effect="plain">{{ item.processing_time }}</el-tag>
              </div>
              <div class="status-indicator" :class="item.status">
                <span class="dot"></span>
                {{ item.status === 'available' ? '可办理' : '暂停办理' }}
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
      
      <el-empty v-if="filteredServices.length === 0" description="暂无相关办事项目" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, User, Reading, DataLine, Document, School, More, Calendar, Clock, List } from '@element-plus/icons-vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const router = useRouter()
const searchKeyword = ref('')
const currentCategory = ref('all')
const services = ref<any[]>([])
const quickLinks = ref<any[]>([])
// 过滤占位/自动生成的链接（如 Resource x / Auto-generated quick link）
const displayQuickLinks = computed(() => {
  return (quickLinks.value || []).filter((l: any) => {
    const name = (l?.name || '').toLowerCase()
    const desc = (l?.description || '').toLowerCase()
    const isPlaceholder = name.startsWith('resource ') || desc.includes('auto-generated')
    return !isPlaceholder
  })
})

const categories = [
  { key: 'all', label: '全部服务', icon: 'More' },
  { key: '学籍管理', label: '学籍管理', icon: 'User' },
  { key: '课程管理', label: '课程管理', icon: 'Reading' },
  { key: '成绩管理', label: '成绩管理', icon: 'DataLine' },
  { key: '证书办理', label: '证书办理', icon: 'Document' },
  { key: '其他服务', label: '其他服务', icon: 'School' }
]

const getCategoryLabel = (key: string) => {
  const cat = categories.find(c => c.key === key)
  return cat ? cat.label : key
}

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
    console.error('获取快捷入口失败', error)
  }
}

const fetchServices = async () => {
  try {
    const token = localStorage.getItem('token')
    console.log('Current Token:', token)
    if (!token) {
      ElMessage.warning('未检测到登录凭证，请重新登录')
      return
    }
    const response = await axios.get('/api/service/list')
    services.value = response.data
  } catch (error) {
    console.error('获取办事项目失败', error)
    ElMessage.error('获取办事项目失败')
  }
}

const handleServiceClick = (item: any) => {
  router.push(`/service/detail/${item.id}`)
}

const handleMyApplications = () => {
  router.push('/service/my-applications')
}

onMounted(() => {
  fetchServices()
  fetchQuickLinks()
})
</script>

<style scoped>
.service-hall {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.title-area h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.subtitle {
  margin: 5px 0 0;
  color: #909399;
  font-size: 14px;
}

.search-area {
  display: flex;
  gap: 15px;
  align-items: center;
}

.search-input {
  width: 300px;
}

.category-nav {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  overflow-x: auto;
  padding-bottom: 10px;
}

.quick-links {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

@media (max-width: 1200px) {
  .quick-links {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .quick-links {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .quick-links {
    grid-template-columns: 1fr;
  }
}

.quick-link-card {
  display: flex;
  align-items: flex-start;
  gap: 15px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid #ebeef5;
  min-height: 110px;
}

.quick-link-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  border-color: #c6e2ff;
}

.quick-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.quick-info {
  flex: 1;
}

.quick-info h4 {
  margin: 0 0 8px;
  font-size: 16px;
  color: #303133;
}

.quick-info p {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

.category-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: white;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid #dcdfe6;
  white-space: nowrap;
}

.category-item:hover {
  color: #409eff;
  border-color: #c6e2ff;
}

.category-item.active {
  background: #409eff;
  color: white;
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

.service-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid #ebeef5;
  display: flex;
  align-items: flex-start;
  gap: 15px;
}

.service-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  border-color: #c6e2ff;
}

.card-icon {
  width: 48px;
  height: 48px;
  background: #ecf5ff;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
  font-size: 24px;
  flex-shrink: 0;
}

.card-content {
  flex: 1;
  overflow: hidden;
}

.card-content h3 {
  margin: 0 0 10px;
  font-size: 16px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tags {
  display: flex;
  gap: 5px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.status-indicator {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.status-indicator.available {
  color: #67c23a;
}

.status-indicator.paused {
  color: #909399;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
</style>
