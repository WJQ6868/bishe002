<template>
  <div class="cert-links-page">
    <!-- 顶部搜索区 -->
    <div class="header-section">
      <div class="title-area">
        <h2>考试证书链接</h2>
        <p class="subtitle">一站式考试报名与证书查询入口</p>
      </div>
      <div class="search-area">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索考试或证书名称..."
          class="search-input"
          :prefix-icon="Search"
          clearable
          @input="handleSearch"
        />
        <el-button type="warning" plain icon="Star" @click="router.push('/cert/my-collections')">
          我的收藏
        </el-button>
        <el-button v-if="isAdmin" type="primary" icon="Plus" @click="openCreateDialog">
          新增链接
        </el-button>
      </div>
    </div>

    <div class="main-content">
      <!-- 左侧：分类与列表 -->
      <div class="left-panel">
        <!-- 分类导航 -->
        <div class="category-nav">
          <div
            v-for="cat in categories"
            :key="cat.key"
            class="category-item"
            :class="{ active: currentCategory === cat.key }"
            @click="handleCategoryChange(cat.key)"
          >
            <el-icon class="cat-icon"><component :is="cat.icon" /></el-icon>
            <span>{{ cat.label }}</span>
          </div>
        </div>

        <!-- 链接列表 -->
        <div class="link-list" v-loading="loading">
          <el-row :gutter="20">
            <el-col
              v-for="link in links"
              :key="link.id"
              :xs="24"
              :sm="12"
              :md="8"
            >
              <div class="link-card" @click="openLink(link)">
                <div class="card-header">
                  <div class="icon-wrapper">
                    <el-icon><component :is="link.icon || 'Link'" /></el-icon>
                  </div>
                  <div class="header-info">
                    <h3>{{ link.name }}</h3>
                    <el-tag v-if="link.is_official" size="small" type="success" effect="plain">官方</el-tag>
                  </div>
                  <div class="collect-btn" @click.stop="toggleCollect(link)">
                    <el-icon :class="{ collected: link.is_collected }">
                      <StarFilled v-if="link.is_collected" />
                      <Star v-else />
                    </el-icon>
                  </div>
                </div>
                <div class="card-desc" :title="link.description">
                  {{ link.description || '暂无描述' }}
                </div>
                <div class="card-footer">
                  <span class="category-tag">{{ link.category }}</span>
                  <span class="click-count">
                    <el-icon><View /></el-icon> {{ link.click_count }}
                  </span>
                </div>
              </div>
            </el-col>
          </el-row>
          <el-empty v-if="links.length === 0" description="暂无相关链接" />
        </div>
      </div>

      <!-- 右侧：热门推荐 -->
      <div class="right-panel">
        <div class="panel-card hot-links">
          <div class="panel-header">
            <h3><el-icon><Trophy /></el-icon> 热门推荐</h3>
          </div>
          <div class="hot-list">
            <div
              v-for="(link, index) in hotLinks"
              :key="link.id"
              class="hot-item"
              @click="openLink(link)"
            >
              <span class="rank" :class="{ top3: index < 3 }">{{ index + 1 }}</span>
              <span class="name">{{ link.name }}</span>
              <span class="hot-val"><el-icon><Star /></el-icon></span>
            </div>
          </div>
        </div>

        <div class="panel-card tips-card">
          <div class="panel-header">
            <h3><el-icon><InfoFilled /></el-icon> 使用说明</h3>
          </div>
          <div class="tips-content">
            <p>1. 点击卡片可直接跳转至官方网站（新窗口打开）。</p>
            <p>2. 点击右上角星号 <el-icon><Star /></el-icon> 可收藏常用链接。</p>
            <p>3. 如发现链接失效，请联系管理员反馈。</p>
          </div>
        </div>
      </div>
    </div>
    <el-dialog v-model="createDialogVisible" title="新增考试证书链接" width="600px">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="createForm.name" placeholder="例如：全国计算机等级考试报名" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="createForm.category" placeholder="选择分类" style="width: 100%">
            <el-option v-for="cat in categories.filter(c => c.key !== 'all')" :key="cat.key" :label="cat.label" :value="cat.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="createForm.icon" placeholder="Element Plus 图标名，默认 Link" />
        </el-form-item>
        <el-form-item label="链接地址" prop="url">
          <el-input v-model="createForm.url" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="简要说明该链接用途" />
        </el-form-item>
        <el-form-item label="标记">
          <el-checkbox v-model="createForm.is_hot">热门</el-checkbox>
          <el-checkbox v-model="createForm.is_official" style="margin-left: 16px">官方</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Search, Star, StarFilled, Link, View, Trophy, InfoFilled,
  Monitor, Reading, Postcard, DataLine, Medal, Van, Microphone, School
} from '@element-plus/icons-vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { io, Socket } from 'socket.io-client'

const router = useRouter()
const loading = ref(false)
const searchKeyword = ref('')
const currentCategory = ref('all')
const links = ref<any[]>([])
const isAdmin = ref(localStorage.getItem('user_role') === 'admin')

const categories = [
  { key: 'all', label: '全部', icon: 'School' },
  { key: '计算机类', label: '计算机类', icon: 'Monitor' },
  { key: '英语类', label: '英语类', icon: 'Reading' },
  { key: '职业资格类', label: '职业资格类', icon: 'Postcard' },
  { key: '专业证书类', label: '专业证书类', icon: 'Medal' },
  { key: '其他', label: '其他', icon: 'Van' }
]

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
    console.error('获取链接失败', error)
    ElMessage.error('获取链接失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  fetchLinks()
}

const handleCategoryChange = (cat: string) => {
  currentCategory.value = cat
  fetchLinks()
}

const openLink = async (link: any) => {
  window.open(link.url, '_blank')
  // Record click asynchronously
  try {
    await axios.post(`/cert/click/${link.id}`)
    link.click_count++
  } catch (e) {
    // Ignore error
  }
}

const toggleCollect = async (link: any) => {
  try {
    const response = await axios.post('/cert/collect', 
      { link_id: link.id },
      { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
    )
    
    if (response.data.status === 'collected') {
      link.is_collected = true
      ElMessage.success('收藏成功')
    } else {
      link.is_collected = false
      ElMessage.success('已取消收藏')
    }
  } catch (error) {
    ElMessage.error('操作失败')
  }
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

// 创建链接弹窗与提交
const createDialogVisible = ref(false)
const createFormRef = ref()
const createForm = ref({
  name: '',
  category: '计算机类',
  icon: 'Link',
  url: '',
  description: '',
  is_hot: false,
  is_official: true
})
const createRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  url: [{ required: true, message: '请输入链接地址', trigger: 'blur' }]
}
const openCreateDialog = () => {
  createDialogVisible.value = true
}
const submitCreate = async () => {
  try {
    await createFormRef.value.validate()
    const resp = await axios.post('/cert/create', createForm.value, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    ElMessage.success('创建成功')
    createDialogVisible.value = false
    // 重置表单
    createForm.value = { name: '', category: '计算机类', icon: 'Link', url: '', description: '', is_hot: false, is_official: true }
    // 刷新列表
    fetchLinks()
    // 通知其他标签页
    localStorage.setItem('cert_links_version', String(Date.now()))
  } catch (e) {
    ElMessage.error('创建失败')
  }
}
</script>

<style scoped>
.cert-links-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  background: var(--card-bg);
  backdrop-filter: blur(10px);
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-color);
}

.title-area h2 {
  margin: 0;
  font-size: 24px;
  color: var(--el-text-color-primary);
}

.subtitle {
  margin: 5px 0 0;
  color: rgba(255, 255, 255, 0.6);
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

.main-content {
  display: flex;
  gap: 20px;
}

.left-panel {
  flex: 1;
}

.right-panel {
  width: 300px;
  flex-shrink: 0;
}

.category-nav {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.category-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--card-bg);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid var(--border-color);
  color: var(--el-text-color-regular);
}

.category-item:hover, .category-item.active {
  color: #fff;
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.2);
}

.link-card {
  background: var(--card-bg);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid var(--border-color);
  height: 140px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.link-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  border-color: #c6e2ff;
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.icon-wrapper {
  width: 40px;
  height: 40px;
  background: rgba(103, 194, 58, 0.15);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #67c23a !important;
  font-size: 20px;
  flex-shrink: 0;
}

.header-info {
  flex: 1;
  overflow: hidden;
}

.header-info h3 {
  margin: 0 0 5px;
  font-size: 16px;
  color: var(--el-text-color-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.collect-btn {
  padding: 5px;
  font-size: 20px;
  color: #dcdfe6;
  transition: color 0.3s;
}

.collect-btn:hover {
  color: #e6a23c;
}

.collect-btn .collected {
  color: #e6a23c;
}

.card-desc {
  font-size: 13px;
  color: #909399;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 10px 0;
  flex: 1;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.category-tag {
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.8) !important;
}

.click-count {
  display: flex;
  align-items: center;
  gap: 4px;
}

.panel-card {
  background: var(--card-bg);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-color);
}

.panel-header {
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 10px;
  margin-bottom: 15px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.hot-item {
  display: flex;
  align-items: center;
  padding: 10px 0;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
}

.hot-item:last-child {
  border-bottom: none;
}

.hot-item:hover .name {
  color: #409eff;
}

.rank {
  width: 20px;
  height: 20px;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8) !important;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  margin-right: 10px;
  font-weight: bold;
}

.rank.top3 {
  background: #f56c6c;
  color: white;
}

.name {
  flex: 1;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-right: 10px;
}

.hot-val {
  color: #f56c6c;
  font-size: 12px;
}

.tips-content {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.6;
}

.tips-content p {
  margin: 5px 0;
}
</style>
