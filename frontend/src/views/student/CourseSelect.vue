<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useCourseListing } from '@/composables/useCourseListing'

// 1. 类型定义
interface Course {
  id: number
  name: string
  credit: number
  teacher: string
  remain: number
  type: 'compulsory' | 'elective'
  time: string
}

interface Volunteer {
  course: Course
  rank: number
}

// 2. 数据源
const { courses: availableCourses, loading: courseLoading, reloadTables } = useCourseListing()

// 3. 状态管理
const courseTypeFilter = ref('') // 筛选条件
const selectedVolunteers = ref<Volunteer[]>([]) // 已选志愿
const submitting = ref(false)

// 4. 计算属性：课程筛选
const filteredCourses = computed(() => {
  const list = availableCourses.value
  if (!courseTypeFilter.value) return list
  return list.filter(c => c.type === courseTypeFilter.value)
})

// 5. 核心逻辑

// 加入志愿（含冲突检测）
const handleAddVolunteer = (course: Course) => {
  // 检查是否已添加
  if (selectedVolunteers.value.some(v => v.course.id === course.id)) {
    ElMessage.warning('该课程已在志愿列表中')
    return
  }
  
  // 检查名额
  if (course.remain <= 0) {
    ElMessage.error('该课程名额已满')
    return
  }
  
  // 检查数量限制
  if (selectedVolunteers.value.length >= 5) {
    ElMessage.warning('最多只能选择5个志愿')
    return
  }

  // 冲突检测
  const conflict = selectedVolunteers.value.find(v => v.course.time === course.time)
  if (conflict) {
    ElMessageBox.confirm(
      `检测到时间冲突：${course.name} 与已选的 ${conflict.course.name} 均为 ${course.time}。是否仍要添加？`,
      '选课冲突提示',
      {
        confirmButtonText: '坚持添加',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(() => {
      addToVolunteers(course)
    }).catch(() => {
      // 取消操作
    })
  } else {
    addToVolunteers(course)
  }
}

const addToVolunteers = (course: Course) => {
  selectedVolunteers.value.push({
    course,
    rank: selectedVolunteers.value.length + 1
  })
  ElMessage.success('添加成功，请确认志愿优先级')
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
    ElMessage.warning('请至少选择一门课程')
    return
  }
  
  ElMessageBox.confirm('确定要提交当前选课志愿吗？提交后不可修改。', '提交确认', {
    type: 'info'
  }).then(() => {
    submitting.value = true
    setTimeout(() => {
      submitting.value = false
      ElMessage.success('选课志愿提交成功（演示环境，不会写入数据库）')
      reloadTables(true)
    }, 1000)
  })
}

// 拖拽排序简单的模拟实现 (这里用简单的上移/下移代替复杂的拖拽库，简化演示)
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
</script>

<template>
  <div class="course-select-container">
    <!-- 顶部提示 -->
    <el-alert
      title="当前阶段：第二轮补选（2025-12-05 至 2025-12-10）"
      type="error"
      effect="dark"
      :closable="false"
      class="top-alert"
    />
    
    <div class="main-content">
      <!-- 左侧筛选与操作 -->
      <div class="left-panel">
        <el-card class="filter-card">
          <template #header>
            <div class="card-header">
              <span>课程筛选</span>
            </div>
          </template>
          <el-select v-model="courseTypeFilter" placeholder="全部课程类型" clearable style="width: 100%">
            <el-option label="专业必修课" value="compulsory" />
            <el-option label="通识选修课" value="elective" />
          </el-select>
          
          <div class="stats-info">
             <p>已选志愿：{{ selectedVolunteers.length }} / 5</p>
             <el-button type="primary" style="width: 100%; margin-top: 10px" @click="handleSubmit" :loading="submitting" :disabled="selectedVolunteers.length === 0">
               提交所有志愿
             </el-button>
          </div>
        </el-card>
        
        <!-- 志愿列表 (简单展示) -->
        <el-card class="volunteer-card" header="已选志愿 (优先级排序)">
          <div v-if="selectedVolunteers.length === 0" class="empty-tip">暂无志愿</div>
          <div v-else class="volunteer-list">
            <div v-for="(item, index) in selectedVolunteers" :key="item.course.id" class="volunteer-item">
              <div class="rank-badge">{{ item.rank }}</div>
              <div class="v-info">
                <div class="v-name">{{ item.course.name }}</div>
                <div class="v-time">{{ item.course.time }}</div>
              </div>
              <div class="v-actions">
                <el-button circle size="small" icon="ArrowUp" @click="moveVolunteer(index, 'up')" :disabled="index === 0" />
                <el-button circle size="small" icon="ArrowDown" @click="moveVolunteer(index, 'down')" :disabled="index === selectedVolunteers.length - 1" />
                <el-button circle size="small" type="danger" icon="Close" @click="handleRemoveVolunteer(index)" />
              </div>
            </div>
          </div>
        </el-card>
      </div>
      
      <!-- 右侧课程列表 -->
      <div class="right-panel">
        <el-card>
          <el-table :data="filteredCourses" style="width: 100%" :loading="courseLoading">
            <el-table-column prop="name" label="课程名称" width="180">
              <template #default="{ row }">
                <span style="font-weight: bold">{{ row.name }}</span>
                <el-tag size="small" v-if="row.type === 'compulsory'" type="danger" style="margin-left: 5px">必修</el-tag>
                <el-tag size="small" v-else type="success" style="margin-left: 5px">选修</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="teacher" label="任课教师" width="100" />
            <el-table-column prop="credit" label="学分" width="80" />
            <el-table-column prop="time" label="上课时间" width="150" />
            <el-table-column prop="remain" label="剩余名额" width="100">
              <template #default="{ row }">
                <span :class="{ 'text-danger': row.remain < 10 }">{{ row.remain }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作">
              <template #default="{ row }">
                <el-button 
                  type="primary" 
                  size="small" 
                  :disabled="row.remain <= 0"
                  @click="handleAddVolunteer(row)"
                >
                  {{ row.remain <= 0 ? '名额已满' : '加入志愿' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.course-select-container {
  height: 100%;
}
.top-alert {
  margin-bottom: 20px;
}
.main-content {
  display: flex;
  gap: 20px;
}
.left-panel {
  width: 350px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.right-panel {
  flex: 1;
}
.stats-info {
  margin-top: 20px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
}
.volunteer-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.volunteer-item {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.03);
  padding: 10px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
}
.rank-badge {
  width: 24px;
  height: 24px;
  background: var(--primary-color);
  color: #000;
  border-radius: 50%;
  text-align: center;
  line-height: 24px;
  margin-right: 10px;
  font-size: 12px;
  font-weight: bold;
}
.v-info {
  flex: 1;
}
.v-name {
  font-weight: bold;
  font-size: 14px;
  color: #fff;
}
.v-time {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}
.v-actions {
  display: flex;
  gap: 5px;
}
.text-danger {
  color: #F56C6C;
  font-weight: bold;
}
.empty-tip {
  text-align: center;
  color: rgba(255, 255, 255, 0.5);
  padding: 20px;
}

:deep(.el-card) {
  background: var(--card-bg) !important;
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-color) !important;
}

:deep(.el-card__header) {
  border-bottom: 1px solid var(--border-color) !important;
  color: #fff !important;
}
</style>
