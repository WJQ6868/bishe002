<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Search } from '@element-plus/icons-vue'
import axios from 'axios'
import { useTables } from '@/composables/useTables'

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

// 当前已选课程（优先走数据库；接口不可用时回退本地缓存）
const selectedCourses = ref<SelectedCourse[]>([])

// 选课历史（优先走数据库成绩记录；接口不可用时回退本地缓存）
const courseHistory = ref<HistoryCourse[]>([])

// --- 3. 状态管理 ---
const activeTab = ref('selected')
const loading = ref(false)
const semesterFilter = ref('')
const statusFilter = ref('')
const searchKeyword = ref('')

const studentAccount = localStorage.getItem('user_account') || ''
const { rows: tableRows, reloadTables } = useTables(['grades', 'courses', 'teachers'])

const teacherMap = computed<Record<string, string>>(() => {
  const map: Record<string, string> = {}
  tableRows('teachers').forEach((t: any) => {
    map[String(t.id)] = t.name || String(t.id)
  })
  return map
})

const courseMap = computed<Record<number, any>>(() => {
  const map: Record<number, any> = {}
  tableRows('courses').forEach((c: any) => {
    map[Number(c.id)] = c
  })
  return map
})

const dbHistory = computed<HistoryCourse[]>(() => {
  const grades = tableRows('grades').filter((g: any) => !studentAccount || g.student_id === studentAccount)
  return grades
    .map((g: any) => {
      const course = courseMap.value[Number(g.course_id)]
      const teacherName = course ? (teacherMap.value[String(course.teacher_id)] || String(course.teacher_id)) : '未设置'
      const semester = course?.create_time ? String(course.create_time).slice(0, 7) : '未分类'
      return {
        id: Number(g.id),
        courseName: course?.name || '未设置课程',
        courseId: course ? String(course.id) : String(g.course_id),
        credit: Number(course?.credit || 0),
        score: g.score == null ? null : Number(g.score),
        semester,
        status: '已完成',
        teacher: teacherName,
      } as HistoryCourse
    })
    .sort((a, b) => String(b.semester).localeCompare(String(a.semester)))
})

const loadSelectedFromDb = async () => {
  const res = await axios.get('/course/student/list', {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  })
  const list = Array.isArray(res.data) ? res.data : []
  const teacherNameById: Record<string, string> = {}

  await Promise.all(list.map(async (c: any) => {
    try {
      const tRes = await axios.get(`/course/${c.id}/teacher`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      })
      teacherNameById[String(c.id)] = tRes.data?.name || ''
    } catch {
      teacherNameById[String(c.id)] = ''
    }
  }))

  selectedCourses.value = list.map((c: any) => {
    const semester = c?.create_time ? String(c.create_time).slice(0, 7) : '未分类'
    return {
      id: Number(c.id),
      courseName: c.name,
      courseId: String(c.id),
      credit: Number(c.credit || 0),
      teacher: teacherNameById[String(c.id)] || String(c.teacher_id || ''),
      time: '—',
      location: '—',
      remain: Number(c.capacity || 0),
      semester,
    }
  })
}

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

// 加载本地数据（兜底）
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

const loadAll = async () => {
  loading.value = true
  try {
    await loadSelectedFromDb()
    await reloadTables(true)
    courseHistory.value = dbHistory.value

    // 缓存一份，便于离线/接口异常时也能展示
    localStorage.setItem('selected_courses', JSON.stringify(selectedCourses.value))
    localStorage.setItem('course_history', JSON.stringify(courseHistory.value))
  } catch (e) {
    loadLocalData()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAll()
})
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
