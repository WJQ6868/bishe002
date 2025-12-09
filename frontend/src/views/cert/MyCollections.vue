<template>
  <div class="my-collections">
    <div class="page-header">
      <div class="header-left">
        <el-button icon="ArrowLeft" @click="router.back()">返回</el-button>
        <h2>我的收藏</h2>
      </div>
    </div>

    <div class="collection-list" v-loading="loading">
      <el-table :data="links" style="width: 100%" border>
        <el-table-column prop="name" label="链接名称" min-width="200">
          <template #default="{ row }">
            <div class="link-name-cell">
              <el-icon><component :is="row.icon || 'Link'" /></el-icon>
              <span class="name">{{ row.name }}</span>
              <el-tag v-if="row.is_official" size="small" type="success" effect="plain">官方</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="description" label="描述" min-width="300" show-overflow-tooltip />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openLink(row)">
              <el-icon><Link /></el-icon> 访问
            </el-button>
            <el-button type="danger" link @click="removeCollection(row)">
              <el-icon><Delete /></el-icon> 取消收藏
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-empty v-if="links.length === 0" description="暂无收藏记录" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Link, Delete } from '@element-plus/icons-vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const links = ref<any[]>([])

const fetchCollections = async () => {
  loading.value = true
  try {
    const response = await axios.get('http://localhost:8000/api/cert/collection/list', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    links.value = response.data
  } catch (error) {
    console.error('获取收藏失败', error)
    ElMessage.error('获取收藏失败')
  } finally {
    loading.value = false
  }
}

const openLink = (link: any) => {
  window.open(link.url, '_blank')
}

const removeCollection = (link: any) => {
  ElMessageBox.confirm(
    '确定要取消收藏该链接吗？',
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    try {
      await axios.post('http://localhost:8000/api/cert/collect', 
        { link_id: link.id },
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      )
      ElMessage.success('已取消收藏')
      fetchCollections() // Refresh list
    } catch (error) {
      ElMessage.error('操作失败')
    }
  }).catch(() => {})
}

onMounted(() => {
  fetchCollections()
})
</script>

<style scoped>
.my-collections {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
  background: white;
  padding: 15px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.collection-list {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.link-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.link-name-cell .name {
  font-weight: 500;
  color: #303133;
}
</style>
