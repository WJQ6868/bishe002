import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import Layout from '../views/Layout.vue'
import Login from '../views/Login.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: '系统登录' }
  },
  {
    path: '/requirements-analysis',
    name: 'RequirementsAnalysis',
    component: () => import('../views/RequirementsAnalysis.vue'),
    meta: { title: '需求分析', roles: ['admin', 'teacher', 'student'] } // 开放给所有角色演示
  },
  {
    path: '/system-architecture',
    name: 'SystemArchitecture',
    component: () => import('../views/SystemArchitecture.vue'),
    meta: { title: '系统架构', roles: ['admin', 'teacher', 'student'] } // 开放给所有角色演示
  },
  {
    path: '/material',
    component: () => import('../layouts/MaterialLayout.vue'),
    redirect: '/material/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'MaterialDashboard',
        component: () => import('../views/material/Dashboard.vue'),
        meta: { title: 'Dashboard', roles: ['admin', 'student', 'teacher'] }
      },
      {
        path: 'instant-message',
        name: 'MaterialInstantMessage',
        component: () => import('../views/material/InstantMessage.vue'),
        meta: { title: 'Chat', roles: ['student', 'teacher'] }
      },
      {
        path: 'student-leave',
        name: 'MaterialStudentLeave',
        component: () => import('../views/material/StudentLeave.vue'),
        meta: { title: 'Leave Request', roles: ['student'] }
      },
      {
        path: 'teacher-leave-approval',
        name: 'MaterialTeacherLeaveApproval',
        component: () => import('../views/material/TeacherLeaveApproval.vue'),
        meta: { title: 'Leave Approval', roles: ['teacher'] }
      },
      {
        path: 'teacher-attendance',
        name: 'MaterialTeacherAttendance',
        component: () => import('../views/material/TeacherAttendance.vue'),
        meta: { title: 'Attendance', roles: ['teacher'] }
      },
      {
        path: 'teacher-homework',
        name: 'MaterialTeacherHomework',
        component: () => import('../views/material/TeacherHomework.vue'),
        meta: { title: 'Homework', roles: ['teacher'] }
      },
      {
        path: 'teacher-work-schedule',
        name: 'MaterialTeacherWorkSchedule',
        component: () => import('../views/material/TeacherWorkSchedule.vue'),
        meta: { title: 'Work Schedule', roles: ['teacher'] }
      },
      {
        path: 'student-homework',
        name: 'MaterialStudentHomework',
        component: () => import('../views/material/StudentHomework.vue'),
        meta: { title: 'Student Homework', roles: ['student'] }
      },
      {
        path: 'calendar',
        name: 'MaterialCalendar',
        component: () => import('../views/material/Calendar.vue'),
        meta: { title: 'Calendar', roles: ['admin', 'teacher', 'student'] }
      },
      {
        path: 'service-hall',
        name: 'MaterialServiceHall',
        component: () => import('../views/material/ServiceHall.vue'),
        meta: { title: 'Service Hall', roles: ['admin', 'teacher', 'student'] }
      },
      {
        path: 'exam-certificates',
        name: 'MaterialExamCertificates',
        component: () => import('../views/material/ExamCertificates.vue'),
        meta: { title: 'Exam Certificates', roles: ['admin', 'teacher', 'student'] }
      },
      {
        path: 'student-course-select',
        name: 'MaterialStudentCourseSelect',
        component: () => import('../views/material/StudentCourseSelect.vue'),
        meta: { title: 'Course Select', roles: ['student'] }
      },
      {
        path: 'student-grade-management',
        name: 'MaterialStudentGradeManagement',
        component: () => import('../views/material/StudentGradeManagement.vue'),
        meta: { title: 'Grade Management', roles: ['student'] }
      },
      {
        path: 'teacher-grade-management',
        name: 'MaterialTeacherGradeManagement',
        component: () => import('../views/material/TeacherGradeManagement.vue'),
        meta: { title: 'Grade Management', roles: ['teacher'] }
      },
      
      {
        path: 'course-management',
        name: 'MaterialCourseManagement',
        component: () => import('../views/material/CourseManagement.vue'),
        meta: { title: 'Course Management', roles: ['admin'] }
      },
      {
        path: 'schedule',
        name: 'MaterialSchedule',
        component: () => import('../views/material/Schedule.vue'),
        meta: { title: 'Schedule Management', roles: ['admin'] }
      },
      {
        path: 'user-management',
        name: 'MaterialUserManagement',
        component: () => import('../views/material/UserManagement.vue'),
        meta: { title: 'User Management', roles: ['admin'] }
      },
      {
        path: 'resource-management',
        name: 'MaterialResourceManagement',
        component: () => import('../views/material/ResourceManagement.vue'),
        meta: { title: 'Resource Management', roles: ['admin'] }
      },
      {
        path: 'reservation-audit',
        name: 'MaterialReservationAudit',
        component: () => import('../views/material/ReservationAudit.vue'),
        meta: { title: 'Reservation Audit', roles: ['admin'] }
      },
      {
        path: 'system-config',
        name: 'MaterialSystemConfig',
        component: () => import('../views/material/SystemConfig.vue'),
        meta: { title: 'System Config', roles: ['admin'] }
      },
      {
        path: 'analysis',
        name: 'MaterialAnalysis',
        component: () => import('../views/material/Analysis.vue'),
        meta: { title: 'Analysis', roles: ['admin', 'teacher'] }
      }
    ]
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '系统首页', icon: 'Odometer', roles: ['admin', 'student', 'teacher'] }
      },
      {
        path: 'course',
        name: 'Course',
        component: () => import('../views/Course.vue'),
        meta: { title: '课程管理', icon: 'Reading', roles: ['admin'] }
      },
      {
        path: 'schedule',
        name: 'Schedule',
        component: () => import('../views/Schedule.vue'),
        meta: { title: '排课管理', icon: 'Calendar', roles: ['admin'] }
      },
      {
        path: 'user-management',
        name: 'UserManagement',
        component: () => import('../views/admin/UserManagement.vue'),
        meta: { title: '用户管理', icon: 'User', roles: ['admin'] }
      },
      {
        path: 'admin/service-approval',
        name: 'ServiceApproval',
        component: () => import('../views/admin/ServiceApproval.vue'),
        meta: { title: '办事审批', icon: 'Stamp', roles: ['admin'] }
      },
      {
        path: 'admin/class-adjust',
        name: 'AdminClassAdjust',
        component: () => import('../views/admin/ClassAdjust.vue'),
        meta: { title: '调课审批', icon: 'Stamp', roles: ['admin'] }
      },
      {
        path: 'resource-management',
        name: 'ResourceManagement',
        component: () => import('../views/ResourceManagement.vue'),
        meta: { title: '教学资源', icon: 'School', roles: ['admin'] }
      },
      {
        path: 'reservation-audit',
        name: 'ReservationAudit',
        component: () => import('../views/ReservationAudit.vue'),
        meta: { title: '预约审核', icon: 'Stamp', roles: ['admin'] }
      },
      {
        path: 'ai-config',
        name: 'AIConfig',
        component: () => import('../views/AIConfig.vue'),
        meta: { title: 'AI客服配置', roles: ['admin'] }
      },
      {
        path: 'system-config',
        name: 'SystemConfig',
        component: () => import('../views/SystemConfig.vue'),
        meta: { title: '系统配置', icon: 'Setting', roles: ['admin'] }
      },
      
      {
        path: 'analysis',
        name: 'Analysis',
        component: () => import('../views/Analysis.vue'),
        meta: { title: '学情分析', icon: 'DataAnalysis', roles: ['admin', 'teacher'] }
      },
      {
        path: 'academic/linkage',
        name: 'AcademicLinkage',
        component: () => import('../views/AcademicLinkage.vue'),
        meta: { title: '专业班级联动', icon: 'Collection', roles: ['admin', 'teacher'] }
      },
      {
        path: 'instant-message',
        name: 'InstantMessage',
        component: () => import('../views/InstantMessage.vue'),
        meta: { title: '即时通讯', icon: 'ChatLineRound', roles: ['student', 'teacher'] }
      },
      {
        path: 'calendar',
        name: 'Calendar',
        component: () => import('../views/Calendar.vue'),
        meta: { title: '校历安排', icon: 'Calendar', roles: ['admin', 'student', 'teacher'] }
      },
      {
        path: 'service/hall',
        name: 'ServiceHall',
        component: () => import('../views/service/ServiceHall.vue'),
        meta: { title: '办事大厅', icon: 'OfficeBuilding', roles: ['admin', 'student', 'teacher'] }
      },
      {
        path: 'service/detail/:id',
        name: 'ServiceDetail',
        component: () => import('../views/service/ServiceDetail.vue'),
        meta: { title: '办事详情', roles: ['admin', 'student', 'teacher'], hidden: true }
      },
      {
        path: 'cert/links',
        name: 'CertLinks',
        component: () => import('../views/cert/CertLinks.vue'),
        meta: { title: '考试证书', icon: 'Link' }
      },
      {
        path: 'cert/my-collections',
        name: 'MyCollections',
        component: () => import('../views/cert/MyCollections.vue'),
        meta: { title: '我的收藏', icon: 'Star' }
      },
      {
        path: 'service/my-applications',
        name: 'MyApplications',
        component: () => import('../views/service/MyApplications.vue'),
        meta: { title: '我的申请', roles: ['student', 'teacher'], hidden: true }
      },
      // Student Routes
      {
        path: 'student/course-select',
        name: 'StudentCourseSelect',
        component: () => import('../views/student/CourseSelect.vue'),
        meta: { title: '选课中心', icon: 'Mouse', roles: ['student'] }
      },
      {
        path: 'student/grade-management',
        name: 'StudentGradeManagement',
        component: () => import('../views/student/GradeManagement.vue'),
        meta: { title: '成绩管理', icon: 'Medal', roles: ['student'] }
      },
      {
        path: 'student/profile-center',
        name: 'StudentProfileCenter',
        component: () => import('../views/student/ProfileCenter.vue'),
        meta: { title: '个人中心', icon: 'User', roles: ['student'] }
      },
      {
        path: 'student/course-management',
        name: 'StudentCourseManagement',
        component: () => import('../views/student/CourseManagement.vue'),
        meta: { title: '选课管理', icon: 'List', roles: ['student'] }
      },
      {
        path: 'student/leave-apply',
        name: 'StudentLeaveApply',
        component: () => import('../views/student/Leave.vue'),
        meta: { title: '请假申请', icon: 'Clock', roles: ['student'] }
      },
      {
        path: 'student/homework',
        name: 'StudentHomework',
        component: () => import('../views/student/Homework.vue'),
        meta: { title: '我的作业', icon: 'Edit', roles: ['student'] }
      },
      {
        path: 'student/attendance',
        name: 'StudentAttendance',
        component: () => import('../views/student/Attendance.vue'),
        meta: { title: '上课签到', icon: 'Aim', roles: ['student'] }
      },
      // Teacher Routes
      
      {
        path: 'teacher/lesson-plan',
        name: 'TeacherLessonPlan',
        component: () => import('../views/teacher/LessonPlan.vue'),
        meta: { title: '智能教案', icon: 'Document', roles: ['teacher'] }
      },
      {
        path: 'teacher/grade-management',
        name: 'TeacherGradeManagement',
        component: () => import('../views/teacher/GradeManagement.vue'),
        meta: { title: '成绩管理', icon: 'Notebook', roles: ['teacher'] }
      },
      {
        path: 'teacher/resource-reservation',
        name: 'TeacherResourceReservation',
        component: () => import('../views/teacher/ResourceReservation.vue'),
        meta: { title: '资源预约', icon: 'Timer', roles: ['teacher'] }
      },
      {
        path: 'teacher/leave-approval',
        name: 'TeacherLeaveApproval',
        component: () => import('../views/teacher/Leave.vue'),
        meta: { title: '请假审批', icon: 'Stamp', roles: ['teacher'] }
      },
      {
        path: 'teacher/attendance',
        name: 'TeacherAttendance',
        component: () => import('../views/teacher/Attendance.vue'),
        meta: { title: '上课点名', icon: 'Aim', roles: ['teacher'] }
      },
      {
        path: 'teacher/homework',
        name: 'TeacherHomework',
        component: () => import('../views/teacher/Homework.vue'),
        meta: { title: '作业管理', icon: 'EditPen', roles: ['teacher'] }
      },
      {
        path: 'teacher/work-schedule',
        name: 'TeacherWorkSchedule',
        component: () => import('../views/teacher/WorkSchedule.vue'),
        meta: { title: '工作安排', icon: 'Calendar', roles: ['teacher'] }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation Guard
router.beforeEach((to, from, next) => {
  const isLogin = localStorage.getItem('is_login') === 'true'
  const userRole = localStorage.getItem('user_role')

  if (to.path === '/login') {
    if (isLogin) {
      // If already logged in, redirect to appropriate page
      if (userRole === 'student') next('/student/course-select')
      else if (userRole === 'teacher') next('/teacher/grade-management')
      else next('/dashboard')
    } else {
      next()
    }
  } else {
    // Requires auth
    if (!isLogin) {
      next('/login')
    } else {
      // Simple role check (for demo purposes, not strict security)
      if (to.meta.roles && Array.isArray(to.meta.roles) && userRole) {
        if (!to.meta.roles.includes(userRole)) {
          // Redirect to home if unauthorized
          next('/dashboard')
        } else {
          next()
        }
      } else {
        next()
      }
    }
  }
})

export default router
