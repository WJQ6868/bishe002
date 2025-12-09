<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Search } from '@element-plus/icons-vue'

// --- 1. 类型定义 ---
/**
 * 当前已选课程
 */
interface SelectedCourse {
  id: number
  courseName: string
  courseId: string
  credit: number
  teacher: string
  time: string
  location: string
  remain: number
  semester: string
}

/**
 * 选课历史记录
 */
interface HistoryCourse {
  id: number
  courseName: string
  courseId: string
  credit: number
  score: number | null
  semester: string
  status: '已完成' | '已退课'
  teacher: string
}

// --- 2. 模拟数据 ---
// 真实场景下需从系统配置接口获取管理员设置的退课周期
const dropDeadline = '2025-12-10 23:59:59'

// 当前已选课程（5门）
const selectedCourses = ref<SelectedCourse[]>([
  {
    id: 1,
    courseName: '数据库原理',
    courseId: 'CS301',
    credit: 4,
    teacher: '黄教授',
    time: '周一 1-2节, 周三 3-4节',
    location: '教学楼A101',
    remain: 5,
    semester: '2024-2025-1'
  },
  {
    id: 2,
    courseName: '软件工程',
    courseId: 'CS302',
    credit: 3,
    teacher: '徐老师',
    time: '周二 5-6节',
    location: '教学楼B203',
    remain: 8,
    semester: '2024-2025-1'
  },
  {
    id: 3,
    courseName: '算法设计',
    courseId: 'CS303',
    credit: 3,
    teacher: '杨教授',
    time: '周四 1-2节',
    location: '教学楼A305',
    remain: 3,
    semester: '2024-2025-1'
  },
  {
    id: 4,
    courseName: '人工智能导论',
    courseId: 'CS304',
    credit: 3,
    teacher: '马老师',
    time: '周五 3-4节',
    location: '教学楼C102',
    remain: 12,
    semester: '2024-2025-1'
  },
  {
    id: 5,
    courseName: 'Web开发技术',
    courseId: 'CS305',
    credit: 2,
    teacher: '冯老师',
    time: '周三 7-8节',
    location: '实验楼201',
    remain: 6,
    semester: '2024-2025-1'
  }
])

// 选课历史（8门）
const courseHistory = ref<HistoryCourse[]>([
  { id: 1, courseName: '高等数学A', courseId: 'MATH101', credit: 4, score: 92, semester: '2023-2024-1', status: '已完成', teacher: '张教授' },
  { id: 2, courseName: '大学英语', courseId: 'ENG101', credit: 3, score: 85, semester: '2023-2024-1', status: '已完成', teacher: '李老师' },
  { id: 3, courseName: '计算机导论', courseId: 'CS101', credit: 3, score: 78, semester: '2023-2024-1', status: '已完成', teacher: '王老师' },
  { id: 4, courseName: '线性代数', courseId: 'MATH102', credit: 3, score: null, semester: '2023-2024-1', status: '已退课', teacher: '赵教授' },
  { id: 5, courseName: '数据结构', courseId: 'CS201', credit: 4, score: 82, semester: '2023-2024-2', status: '已完成', teacher: '陈教授' },
  { id: 6, courseName: '概率论', courseId: 'MATH201', credit: 3, score: 75, semester: '2023-2024-2', status: '已完成', teacher: '周老师' },
  { id: 7, courseName: '操作系统', courseId: 'CS202', credit: 3, score: 86, semester: '2023-2024-2', status: '已完成', teacher: '吴教授' },
  { id: 8, courseName: '大学物理', courseId: 'PHY101', credit: 3, score: null, semester: '2023-2024-2', status: '已退课', teacher: '孙教授' }
])

// --- 3. 状态管理 ---
const activeTab = ref('selected')
const loading = ref(false)
const semesterFilter = ref('')
const statusFilter = ref('')
const searchKeyword = ref('')

// 退课截止时间判断
const isDropAllowed = computed(() => {
  const now = new Date()
  const deadline = new Date(dropDeadline)
  return now < deadline
})

// 倒计时
const countdown = computed(() => {
  if (!isDropAllowed.value) return '退课已截止'
  
  const now = new Date()
  const deadline = new Date(dropDeadline)
  const diff = deadline.getTime() - now.getTime()
  
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
  
  return `距离退课截止还有 ${days}天 ${hours}小时 ${minutes}分钟`
})

// 学期列表
const semesters = computed(() => {
  const set = new Set(courseHistory.value.map(c => c.semester))
  return Array.from(set).sort().reverse()
})

// 筛选后的历史记录
const filteredHistory = computed(() => {
  let result = courseHistory.value
  
  if (semesterFilter.value) {
    result = result.filter(c => c.semester === semesterFilter.value)
  }
  
  if (statusFilter.value) {
    result = result.filter(c => c.status === statusFilter.value)
  }
  
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(c => 
      c.courseName.toLowerCase().includes(keyword) ||
      c.courseId.toLowerCase().includes(keyword)
    )
  }
  
  return result
})

// --- 4. 核心逻辑 ---

/**
 * 退课操作
 * 退课规则说明：退课仅允许在选课周期结束后1周内办理
 */
const dropCourse = (course: SelectedCourse) => {
  if (!isDropAllowed.value) {
    ElMessage.warning('退课截止时间已过，无法办理退课')
    return
  }
  
  ElMessageBox.confirm(
    `确定要退选《${course.courseName}》吗？退课后不可恢复！`,
    '退课确认',
    {
      confirmButtonText: '确定退课',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger'
    }
  ).then(() => {
    // 从已选课程中移除
    const index = selectedCourses.value.findIndex(c => c.id === course.id)
    if (index !== -1) {
      selectedCourses.value.splice(index, 1)
      
      // 添加到历史记录
      courseHistory.value.unshift({
        id: Date.now(),
        courseName: course.courseName,
        courseId: course.courseId,
        credit: course.credit,
        score: null,
        semester: course.semester,
        status: '已退课',
        teacher: course.teacher
      })
      
      // 保存到 localStorage
      localStorage.setItem('selected_courses', JSON.stringify(selectedCourses.value))
      localStorage.setItem('course_history', JSON.stringify(courseHistory.value))
      
      ElMessage.success('退课成功')
    }
  }).catch(() => {
    // 用户取消
  })
}

// 加载本地数据
const loadLocalData = () => {
  const savedSelected = localStorage.getItem('selected_courses')
  if (savedSelected) {
    selectedCourses.value = JSON.parse(savedSelected)
  }
  
  const savedHistory = localStorage.getItem('course_history')
  if (savedHistory) {
    courseHistory.value = JSON.parse(savedHistory)
  }
}

loadLocalData()
</script>

<template>
  <div class="course-management-container">
    <!-- 顶部提示 -->
    <el-alert
      :title="countdown"
      type="warning"
      :closable="false"
      style="margin-bottom: 20px"
    >
      <template #default>
        <div class="drop-notice">
          <p><strong>退课须知：</strong></p>
          <ul>
            <li>退课仅允许在选课周期结束后1周内办理</li>
            <li>退课后课程名额将释放，其他同学可继续选课</li>
            <li>退课操作不可恢复，请谨慎操作</li>
            <li>退课截止时间：<span class="deadline">{{ dropDeadline }}</span></li>
          </ul>
        </div>
      </template>
    </el-alert>

    <!-- 标签页 -->
    <el-card>
      <el-tabs v-model="activeTab">
        <!-- 当前已选 -->
        <el-tab-pane label="当前已选" name="selected">
          <div class="selected-header">
            <h3>已选课程列表（{{ selectedCourses.length }}/5）</h3>
          </div>
          
          <el-table
            v-loading="loading"
            :data="selectedCourses"
            style="width: 100%"
          >
            <el-table-column prop="courseName" label="课程名称" min-width="150" />
            <el-table-column prop="courseId" label="课程号" width="100" />
            <el-table-column prop="credit" label="学分" width="80" align="center" />
            <el-table-column prop="teacher" label="教师" width="100" />
            <el-table-column prop="time" label="上课时间" min-width="180" />
            <el-table-column prop="location" label="上课地点" width="120" />
            <el-table-column prop="remain" label="剩余名额" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.remain < 5 ? 'danger' : 'success'" size="small">
                  {{ row.remain }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button
                  link
                  type="danger"
                  :icon="Delete"
                  :disabled="!isDropAllowed"
                  @click="dropCourse(row)"
                >
                  {{ isDropAllowed ? '退课' : '已截止' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 选课历史 -->
        <el-tab-pane label="选课历史" name="history">
          <div class="history-header">
            <h3>选课历史记录</h3>
            <div class="history-filters">
              <el-select v-model="semesterFilter" placeholder="选择学期" style="width: 150px; margin-right: 10px" clearable>
                <el-option v-for="sem in semesters" :key="sem" :label="sem" :value="sem" />
              </el-select>
              <el-select v-model="statusFilter" placeholder="选课状态" style="width: 120px; margin-right: 10px" clearable>
                <el-option label="已完成" value="已完成" />
                <el-option label="已退课" value="已退课" />
              </el-select>
              <el-input
                v-model="searchKeyword"
                placeholder="搜索课程名称/课程号"
                style="width: 200px"
                clearable
                :prefix-icon="Search"
              />
            </div>
          </div>
          
          <el-table
            v-loading="loading"
            :data="filteredHistory"
            style="width: 100%"
            :row-class-name="({ row }) => row.status === '已退课' ? 'dropped-row' : ''"
          >
            <el-table-column prop="courseName" label="课程名称" min-width="150" />
            <el-table-column prop="courseId" label="课程号" width="100" />
            <el-table-column prop="credit" label="学分" width="80" align="center" />
            <el-table-column prop="score" label="成绩" width="80" align="center">
              <template #default="{ row }">
                <span v-if="row.score !== null">{{ row.score }}</span>
                <span v-else style="color: #909399">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="semester" label="选课学期" width="130" />
            <el-table-column prop="status" label="选课状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === '已完成' ? 'success' : 'info'" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="teacher" label="教师姓名" width="100" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style scoped>
.course-management-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.drop-notice {
  font-size: 14px;
  line-height: 1.8;
}
.drop-notice ul {
  margin: 10px 0 0 20px;
  padding: 0;
}
.drop-notice li {
  margin-bottom: 5px;
}
.deadline {
  color: #F56C6C;
  font-weight: 600;
}
.selected-header, .history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.selected-header h3, .history-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.history-filters {
  display: flex;
  gap: 10px;
}
/* 已退课行样式 */
:deep(.el-table .dropped-row) {
  background: #F5F7FA;
  color: #909399;
}
/* 表格 hover 效果（学生端蓝色） */
:deep(.el-table__body tr:hover > td) {
  background-color: #E6F7FF !important;
}
/* 退课按钮样式 */
:deep(.el-button--danger.is-link:hover) {
  color: #C0392B;
}
</style>
