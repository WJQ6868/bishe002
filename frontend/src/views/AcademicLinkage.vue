<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  fetchMajors,
  fetchClasses,
  fetchStudents,
  fetchCourses,
  fetchCourseTeachers,
  type MajorItem,
  type ClassItem,
  type StudentItem,
  type CourseItem,
  type TeacherItem
} from '@/api/academic'

const majors = ref<MajorItem[]>([])
const classes = ref<ClassItem[]>([])
const students = ref<StudentItem[]>([])
const courses = ref<CourseItem[]>([])
const teachersMap = reactive<Record<number, TeacherItem[]>>({})
const teachersLoading = reactive<Record<number, boolean>>({})

const clearTeacherState = () => {
  Object.keys(teachersMap).forEach((key) => {
    delete teachersMap[Number(key)]
  })
  Object.keys(teachersLoading).forEach((key) => {
    delete teachersLoading[Number(key)]
  })
}

const selectedMajor = ref<number | null>(null)
const selectedClass = ref<number | null>(null)
const selectedCourse = ref<number | null>(null)

const loading = reactive({
  majors: false,
  classes: false,
  students: false,
  courses: false
})

const studentHeaders = [
  { title: '学号', key: 'student_code' },
  { title: '姓名', key: 'name' }
]

const loadMajors = async () => {
  loading.majors = true
  try {
    majors.value = await fetchMajors()
  } finally {
    loading.majors = false
  }
}

const handleMajorChange = async (majorId: number | null) => {
  selectedMajor.value = majorId
  selectedClass.value = null
  selectedCourse.value = null
  classes.value = []
  students.value = []
  courses.value = []
  clearTeacherState()
  if (!majorId) return

  loading.classes = true
  try {
    classes.value = await fetchClasses(majorId)
  } finally {
    loading.classes = false
  }
}

const handleClassSelect = async (classId: number) => {
  if (selectedClass.value === classId) return
  selectedClass.value = classId
  selectedCourse.value = null
  students.value = []
  courses.value = []
  clearTeacherState()

  loading.students = true
  loading.courses = true
  try {
    const [stu, courseList] = await Promise.all([
      fetchStudents(classId),
      selectedMajor.value ? fetchCourses(selectedMajor.value) : Promise.resolve([])
    ])
    students.value = stu
    courses.value = courseList
  } finally {
    loading.students = false
    loading.courses = false
  }
}

const loadCourseTeachers = async (courseId: number) => {
  if (teachersMap[courseId]) return
  teachersLoading[courseId] = true
  try {
    teachersMap[courseId] = await fetchCourseTeachers(courseId)
  } finally {
    teachersLoading[courseId] = false
  }
}

const handleCourseClick = async (courseId: number) => {
  selectedCourse.value = courseId
  await loadCourseTeachers(courseId)
}

onMounted(() => {
  loadMajors()
})
</script>

<template>
  <v-container fluid class="academic-linkage">
    <v-row>
      <v-col cols="12">
        <v-select
          label="选择专业"
          :items="majors"
          :loading="loading.majors"
          item-title="name"
          item-value="id"
          density="comfortable"
          clearable
          v-model="selectedMajor"
          @update:model-value="handleMajorChange"
        />
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" md="3">
        <v-card class="h-100">
          <v-card-title>班级列表</v-card-title>
          <v-divider />
          <v-card-text>
            <v-skeleton-loader v-if="loading.classes" type="list-item-two-line" :loading="true" />
            <v-alert v-else-if="!selectedMajor" type="info" variant="tonal">
              请选择专业以查看班级
            </v-alert>
            <v-list v-else>
              <v-list-item
                v-for="clazz in classes"
                :key="clazz.id"
                :active="clazz.id === selectedClass"
                @click="handleClassSelect(clazz.id)"
                class="class-item"
              >
                <v-list-item-title>{{ clazz.name }}</v-list-item-title>
                <v-list-item-subtitle>人数：{{ clazz.student_count }}</v-list-item-subtitle>
              </v-list-item>
              <v-alert v-if="!classes.length" type="warning" class="mt-4" dense>
                暂无班级数据
              </v-alert>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="5">
        <v-card class="h-100">
          <v-card-title>学生列表</v-card-title>
          <v-divider />
          <v-card-text>
            <v-skeleton-loader v-if="loading.students" type="table" />
            <v-alert v-else-if="!selectedClass" type="info" variant="tonal">
              请选择班级以查看学生
            </v-alert>
            <v-data-table
              v-else
              :headers="studentHeaders"
              :items="students"
              :items-per-page="10"
              density="compact"
              :no-data-text="'暂无学生数据'"
            />
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card class="h-100">
          <v-card-title>课程与授课教师</v-card-title>
          <v-divider />
          <v-card-text>
            <v-skeleton-loader v-if="loading.courses" type="card" />
            <v-alert v-else-if="!selectedClass" type="info" variant="tonal">
              请选择班级以加载课程
            </v-alert>
            <div v-else>
              <v-row>
                <v-col
                  cols="12"
                  sm="6"
                  v-for="course in courses"
                  :key="course.id"
                  class="pb-2"
                >
                  <v-card
                    :elevation="selectedCourse === course.id ? 8 : 2"
                    class="course-card"
                    @click="handleCourseClick(course.id)"
                  >
                    <v-card-title class="text-subtitle-1">
                      {{ course.name }}
                    </v-card-title>
                    <v-card-subtitle>
                      学分：{{ course.credit }} ｜ 课时：{{ course.class_hours }}
                    </v-card-subtitle>
                    <v-card-text>
                      <v-skeleton-loader
                        v-if="teachersLoading[course.id]"
                        type="chip"
                        class="py-2"
                      />
                      <template v-else>
                        <v-chip
                          v-for="teacher in teachersMap[course.id]"
                          :key="teacher.teacher_id"
                          size="small"
                          class="ma-1"
                          color="primary"
                          variant="outlined"
                        >
                          {{ teacher.name }}
                        </v-chip>
                        <v-alert
                          v-if="(teachersMap[course.id] || []).length === 0"
                          type="warning"
                          variant="tonal"
                          density="comfortable"
                        >
                          点击卡片加载授课教师
                        </v-alert>
                      </template>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
              <v-alert v-if="!courses.length" type="warning" class="mt-4" dense>
                暂无课程数据
              </v-alert>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<style scoped>
.academic-linkage {
  min-height: calc(100vh - 120px);
}

.class-item {
  cursor: pointer;
}

.course-card {
  cursor: pointer;
  transition: box-shadow 0.2s ease;
}
</style>
