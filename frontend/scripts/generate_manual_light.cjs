const fs = require('fs')
const path = require('path')
const puppeteer = require('puppeteer')
const { Document, Packer, Paragraph, HeadingLevel, ImageRun, TableOfContents, PageBreak } = require('docx')

const BASE_URL = 'http://localhost:2003'
const OUT_DIR = path.join(__dirname, '..', 'manual')
const IMG_DIR = path.join(OUT_DIR, 'screens')
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true })
if (!fs.existsSync(IMG_DIR)) fs.mkdirSync(IMG_DIR, { recursive: true })

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

async function main() {
  const browser = await puppeteer.launch({ headless: 'new' })
  const page = await browser.newPage()
  await page.setViewport({ width: 1440, height: 900 })

  // Login page
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' })
  const loginPng = path.join(IMG_DIR, 'login.png')
  await page.screenshot({ path: loginPng, fullPage: true })

  // Admin dashboard
  await setRole(page, 'admin')
  await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded' })
  const adminPng = path.join(IMG_DIR, 'admin_dashboard.png')
  await page.screenshot({ path: adminPng, fullPage: true })

  // Teacher grade management
  await setRole(page, 'teacher')
  await page.goto(`${BASE_URL}/teacher/grade-management`, { waitUntil: 'domcontentloaded' })
  const teacherPng = path.join(IMG_DIR, 'teacher_grade.png')
  await page.screenshot({ path: teacherPng, fullPage: true })

  // Student course select
  await setRole(page, 'student')
  await page.goto(`${BASE_URL}/student/course-select`, { waitUntil: 'domcontentloaded' })
  const studentPng = path.join(IMG_DIR, 'student_course_select.png')
  await page.screenshot({ path: studentPng, fullPage: true })

  await page.close()
  await browser.close()

  const doc = new Document({ sections: [ { children: [
    new Paragraph({ text: '高校智能教务系统 前端用户使用手册（精简版）', heading: HeadingLevel.TITLE }),
    new TableOfContents('目录', { hyperlink: true }),
    new PageBreak(),
    new Paragraph({ text: '登录界面', heading: HeadingLevel.HEADING_1 }),
    new Paragraph({ children: [ new ImageRun({ data: fs.readFileSync(loginPng), transformation: { width: 900, height: 506 } }) ] }),
    new PageBreak(),
    new Paragraph({ text: '管理员-系统首页', heading: HeadingLevel.HEADING_1 }),
    new Paragraph({ children: [ new ImageRun({ data: fs.readFileSync(adminPng), transformation: { width: 900, height: 506 } }) ] }),
    new PageBreak(),
    new Paragraph({ text: '教师-成绩管理', heading: HeadingLevel.HEADING_1 }),
    new Paragraph({ children: [ new ImageRun({ data: fs.readFileSync(teacherPng), transformation: { width: 900, height: 506 } }) ] }),
    new PageBreak(),
    new Paragraph({ text: '学生-选课中心', heading: HeadingLevel.HEADING_1 }),
    new Paragraph({ children: [ new ImageRun({ data: fs.readFileSync(studentPng), transformation: { width: 900, height: 506 } }) ] }),
  ] } ] })

  const buffer = await Packer.toBuffer(doc)
  let outDoc = path.join(OUT_DIR, '用户使用手册_精简版.docx')
  try { fs.writeFileSync(outDoc, buffer) } catch { outDoc = path.join(OUT_DIR, 'user_manual_light.docx'); fs.writeFileSync(outDoc, buffer) }
  console.log('[OK] 文档生成：', outDoc)
}

main().catch((e) => { console.error(e); process.exit(1) })

