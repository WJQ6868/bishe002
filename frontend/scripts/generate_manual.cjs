const fs = require('fs')
const path = require('path')
const puppeteer = require('puppeteer')
const { Document, Packer, Paragraph, HeadingLevel, ImageRun, TableOfContents, PageBreak } = require('docx')

const BASE_URL = process.env.BASE_URL || 'http://localhost:2003'
const OUT_DIR = path.join(__dirname, '..', 'manual')
const IMG_DIR = path.join(OUT_DIR, 'screens')

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })
}

const routes = {
  login: [{ path: '/login', name: '登录界面' }],
  admin: [
    { path: '/dashboard', name: '管理员-系统首页' },
    { path: '/service/hall', name: '管理员-办事大厅' },
    { path: '/cert/links', name: '管理员-考试证书' },
    { path: '/course', name: '管理员-课程管理' },
    { path: '/schedule', name: '管理员-排课管理' },
    { path: '/user-management', name: '管理员-用户管理' },
    { path: '/admin/service-approval', name: '管理员-办事审批' },
    { path: '/admin/class-adjust', name: '管理员-调课审批' },
    { path: '/resource-management', name: '管理员-教学资源' },
    { path: '/reservation-audit', name: '管理员-预约审核' },
    { path: '/ai-config', name: '管理员-AI客服配置' },
    { path: '/system-config', name: '管理员-系统配置' },
    { path: '/analysis', name: '管理员-学情分析' },
    { path: '/instant-message', name: '管理员-即时通讯' },
    { path: '/academic/linkage', name: '管理员-专业班级联动' }
  ],
  teacher: [
    { path: '/teacher/grade-management', name: '教师-成绩管理' },
    { path: '/teacher/attendance', name: '教师-上课点名' },
    { path: '/teacher/homework', name: '教师-作业管理' },
    { path: '/teacher/work-schedule', name: '教师-工作安排' },
    { path: '/teacher/leave-approval', name: '教师-请假审批' },
    { path: '/teacher/resource-reservation', name: '教师-资源预约' },
    { path: '/instant-message', name: '教师-即时通讯' },
    { path: '/cert/links', name: '教师-考试证书' },
    { path: '/ai-qa', name: '教师-AI智能助手' }
  ],
  student: [
    { path: '/student/course-select', name: '学生-选课中心' },
    { path: '/student/course-management', name: '学生-选课管理' },
    { path: '/student/grade-management', name: '学生-成绩管理' },
    { path: '/student/homework', name: '学生-我的作业' },
    { path: '/student/attendance', name: '学生-上课签到' },
    { path: '/student/profile-center', name: '学生-个人中心' },
    { path: '/instant-message', name: '学生-即时通讯' },
    { path: '/cert/links', name: '学生-考试证书' },
    { path: '/ai-qa', name: '学生-AI智能助手' }
  ]
}

async function setRole(page, role) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' })
  await page.evaluate((r) => {
    localStorage.setItem('is_login', 'true')
    localStorage.setItem('user_role', r)
    localStorage.setItem('user_account', r + '01')
    localStorage.setItem('user_id', r === 'admin' ? '1' : r === 'teacher' ? '2' : '3')
    localStorage.setItem('token', 'FAKE_TOKEN_FOR_SCREENSHOT')
  }, role)
}

async function capture(browser, routeList, prefix) {
  const page = await browser.newPage()
  await page.setViewport({ width: 1440, height: 900 })
  if (prefix !== 'login') {
    await setRole(page, prefix)
  }
  const images = []
  for (const r of routeList) {
    const url = `${BASE_URL}${r.path}`
    const filename = `${prefix}_${r.path.replace(/\//g, '_') || 'root'}.png`.replace(/_+/g, '_')
    const outPath = path.join(IMG_DIR, filename)
    try {
      await page.goto(url, { waitUntil: 'networkidle0', timeout: 30000 })
    } catch {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 })
    }
    try { await page.waitForSelector('body', { timeout: 5000 }) } catch {}
    await page.screenshot({ path: outPath, fullPage: true })
    images.push({ title: r.name, path: outPath })
  }
  await page.close()
  return images
}

async function buildDoc(imagesBySection) {
  const children = [
    new Paragraph({ text: '高校智能教务系统 前端用户使用手册', heading: HeadingLevel.TITLE }),
    new Paragraph({ text: '版本：自动生成', spacing: { after: 200 } }),
    new TableOfContents('目录', { hyperlink: true, headingStyleRange: '1-5' }),
    new PageBreak(),
    new Paragraph({ text: '登录界面', heading: HeadingLevel.HEADING_1 }),
  ]

  for (const item of imagesBySection.login) {
    const img = new ImageRun({ data: fs.readFileSync(item.path), transformation: { width: 900, height: 506 } })
    children.push(new Paragraph({ text: item.title, heading: HeadingLevel.HEADING_2 }))
    children.push(new Paragraph({ children: [img] }))
    children.push(new Paragraph({ text: '（说明：包含按钮、输入框、选择框等交互区域，请结合截图识别具体位置）', spacing: { after: 200 } }))
    children.push(new PageBreak())
  }

  children.push(new Paragraph({ text: '管理员界面', heading: HeadingLevel.HEADING_1 }))
  for (const item of imagesBySection.admin) {
    const img = new ImageRun({ data: fs.readFileSync(item.path), transformation: { width: 900, height: 506 } })
    children.push(new Paragraph({ text: item.title, heading: HeadingLevel.HEADING_2 }))
    children.push(new Paragraph({ children: [img] }))
    children.push(new Paragraph({ text: '（说明：包含按钮、输入框、选择框等交互区域，请结合截图识别具体位置）', spacing: { after: 200 } }))
    children.push(new PageBreak())
  }

  children.push(new Paragraph({ text: '教师界面', heading: HeadingLevel.HEADING_1 }))
  for (const item of imagesBySection.teacher) {
    const img = new ImageRun({ data: fs.readFileSync(item.path), transformation: { width: 900, height: 506 } })
    children.push(new Paragraph({ text: item.title, heading: HeadingLevel.HEADING_2 }))
    children.push(new Paragraph({ children: [img] }))
    children.push(new Paragraph({ text: '（说明：包含按钮、输入框、选择框等交互区域，请结合截图识别具体位置）', spacing: { after: 200 } }))
    children.push(new PageBreak())
  }

  children.push(new Paragraph({ text: '学生界面', heading: HeadingLevel.HEADING_1 }))
  for (const item of imagesBySection.student) {
    const img = new ImageRun({ data: fs.readFileSync(item.path), transformation: { width: 900, height: 506 } })
    children.push(new Paragraph({ text: item.title, heading: HeadingLevel.HEADING_2 }))
    children.push(new Paragraph({ children: [img] }))
    children.push(new Paragraph({ text: '（说明：包含按钮、输入框、选择框等交互区域，请结合截图识别具体位置）', spacing: { after: 200 } }))
    children.push(new PageBreak())
  }

  const doc = new Document({ sections: [{ children }] })
  const buffer = await Packer.toBuffer(doc)
  let outDoc = path.join(OUT_DIR, '用户使用手册.docx')
  try {
    fs.writeFileSync(outDoc, buffer)
  } catch (e) {
    outDoc = path.join(OUT_DIR, 'user_manual.docx')
    fs.writeFileSync(outDoc, buffer)
  }
  return outDoc
}

;(async () => {
  if (!process.env.PUPPETEER_PRODUCT) {
    process.env.PUPPETEER_PRODUCT = 'chrome'
  }
  ensureDir(OUT_DIR)
  ensureDir(IMG_DIR)
  const browser = await puppeteer.launch({ headless: 'new' })
  try {
    const loginImgs = await capture(browser, routes.login, 'login')
    const adminImgs = await capture(browser, routes.admin, 'admin')
    const teacherImgs = await capture(browser, routes.teacher, 'teacher')
    const studentImgs = await capture(browser, routes.student, 'student')

    // 生成分册，避免单个文档过大
    const buildDocRole = async (title, imgs, outName) => {
      const children = [
        new Paragraph({ text: '高校智能教务系统 前端用户使用手册 - ' + title, heading: HeadingLevel.TITLE }),
        new TableOfContents('目录', { hyperlink: true }),
        new PageBreak(),
      ]
      for (const item of imgs) {
        const img = new ImageRun({ data: fs.readFileSync(item.path), transformation: { width: 900, height: 506 } })
        children.push(new Paragraph({ text: item.title, heading: HeadingLevel.HEADING_1 }))
        children.push(new Paragraph({ children: [img] }))
        children.push(new PageBreak())
      }
      const doc = new Document({ sections: [{ children }] })
      const buffer = await Packer.toBuffer(doc)
      const outDoc = path.join(OUT_DIR, outName)
      fs.writeFileSync(outDoc, buffer)
      return outDoc
    }

    const adminDoc = await buildDocRole('管理员', adminImgs, '用户使用手册_管理员.docx')
    const teacherDoc = await buildDocRole('教师', teacherImgs, '用户使用手册_教师.docx')
    const studentDoc = await buildDocRole('学生', studentImgs, '用户使用手册_学生.docx')
    const loginDoc = await buildDocRole('登录', loginImgs, '用户使用手册_登录.docx')
    console.log('[OK] 文档生成：', adminDoc, teacherDoc, studentDoc, loginDoc)
  } catch (e) {
    console.error('生成失败：', e)
    process.exitCode = 1
  } finally {
    await browser.close()
  }
})()
