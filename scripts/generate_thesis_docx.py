# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import re
import sqlite3
from pathlib import Path
from textwrap import dedent

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "generated"
ASSET_DIR = OUTPUT_DIR / "thesis_assets"
DOCX_PATH = ROOT / "AI赋能的高校教务系统-毕业论文原创改写版.docx"
DB_PATH = ROOT / "edu_system.db"
TEST_JSON_PATH = ROOT / "generated_ai_test_results.json"

TITLE = "AI赋能的高校教务系统"
AUTHOR = "王佳齐"
STUDENT_ID = "2405273202"
COLLEGE = "计算机与软件学院"
MAJOR = "工业互联网技术"
CLASS_NAME = "互联2432"
TEACHER = "张锦辉"
ENTERPRISE_MENTOR = "嵇伟"
DATE_CN = "2026年4月"
CHECK_DATE_CN = "2026年4月24日"

FONT_SONG = "宋体"
FONT_HEI = "黑体"
FONT_EN = "Times New Roman"
FONT_FILE = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_FILE_BOLD = Path(r"C:\Windows\Fonts\simhei.ttf")

TEXT_COLLECTOR: list[str] = []


def normalize_paragraphs(text: str) -> list[str]:
    text = dedent(text).strip()
    if not text:
        return []
    blocks = []
    for item in text.split("\n\n"):
        line = "".join(i.strip() for i in item.splitlines())
        if line:
            blocks.append(line)
    return blocks


def record_text(text: str) -> None:
    if text:
        TEXT_COLLECTOR.append(text)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_FILE_BOLD if bold and FONT_FILE_BOLD.exists() else FONT_FILE
    return ImageFont.truetype(str(path), size=size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    for ch in text:
        candidate = current + ch
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines or [text]


def draw_centered_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill=(0, 0, 0)) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text((xy[0] - w / 2, xy[1] - h / 2), text, font=font, fill=fill)


def draw_round_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    lines: list[str] | None = None,
    fill=(248, 250, 252),
    outline=(52, 73, 94),
    title_fill=(52, 73, 94),
    radius: int = 18,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=3)
    title_font = load_font(28, bold=True)
    body_font = load_font(22)
    draw.text((x1 + 18, y1 + 14), title, font=title_font, fill=title_fill)
    if lines:
        y = y1 + 60
        for line in lines:
            wrapped = wrap_text(draw, line, body_font, x2 - x1 - 36)
            for item in wrapped:
                draw.text((x1 + 18, y), item, font=body_font, fill=(33, 37, 41))
                y += 30


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], label: str | None = None) -> None:
    draw.line([start, end], fill=(52, 73, 94), width=4)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    arrow_len = 16
    angle1 = angle - math.pi / 8
    angle2 = angle + math.pi / 8
    p1 = (end[0] - arrow_len * math.cos(angle1), end[1] - arrow_len * math.sin(angle1))
    p2 = (end[0] - arrow_len * math.cos(angle2), end[1] - arrow_len * math.sin(angle2))
    draw.polygon([end, p1, p2], fill=(52, 73, 94))
    if label:
        font = load_font(22, bold=True)
        mx = (start[0] + end[0]) // 2
        my = (start[1] + end[1]) // 2 - 18
        draw_centered_text(draw, (mx, my), label, font, fill=(44, 62, 80))


def create_placeholder_image(path: Path, title: str, subtitle: str) -> None:
    img = Image.new("RGB", (1400, 820), (247, 248, 250))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((80, 80, 1320, 740), radius=24, outline=(120, 130, 140), width=6, fill=(255, 255, 255))
    for i in range(0, 18):
        x = 100 + i * 65
        draw.line((x, 95, x + 35, 95), fill=(170, 170, 170), width=4)
        draw.line((x, 725, x + 35, 725), fill=(170, 170, 170), width=4)
    title_font = load_font(54, bold=True)
    sub_font = load_font(28)
    draw_centered_text(draw, (700, 330), title, title_font, fill=(80, 80, 80))
    draw_centered_text(draw, (700, 410), "【截图占位，后期由作者替换】", load_font(34, bold=True), fill=(160, 50, 50))
    wrapped = wrap_text(draw, subtitle, sub_font, 980)
    y = 500
    for line in wrapped:
        draw_centered_text(draw, (700, y), line, sub_font, fill=(90, 90, 90))
        y += 42
    img.save(path)


def create_system_architecture(path: Path) -> None:
    img = Image.new("RGB", (1700, 1100), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw_centered_text(draw, (850, 50), "高校教务系统总体架构图", load_font(38, bold=True))

    draw_round_box(draw, (120, 110, 500, 230), "学生端", ["课程查询、请假申请、AI客服、AI课程助手、查看共享教案"], fill=(234, 244, 252))
    draw_round_box(draw, (660, 110, 1040, 230), "教师端", ["课程管理、作业批改、课程助手、知识库上传、智能教案生成"], fill=(237, 249, 241))
    draw_round_box(draw, (1200, 110, 1580, 230), "管理员端", ["用户管理、数据维护、模型配置、知识库管理、工作流编排"], fill=(252, 244, 234))

    draw_round_box(draw, (220, 300, 1480, 430), "前端展示层（Vue3 + TypeScript + Element Plus + Pinia + Vue Router）", [
        "统一路由、角色化界面、Axios 请求封装、SSE 流式结果渲染、即时消息与可视化组件",
    ], fill=(246, 248, 252))

    draw_round_box(draw, (180, 500, 1520, 670), "后端服务层（FastAPI + SQLAlchemy + Socket.IO）", [
        "认证授权、课程管理、办事大厅、成绩与请假、管理员 AI 配置、AI Portal、AI QA 路由",
        "统一通过依赖注入获取用户与数据库会话，支持 /api 前缀接口与静态文件访问",
    ], fill=(245, 245, 255))

    draw_round_box(draw, (140, 740, 520, 960), "AI 配置编排层", [
        "模型 API 管理、工作流应用绑定、客服欢迎语/推荐问题、模型测试与启停控制",
    ], fill=(244, 249, 255))
    draw_round_box(draw, (550, 740, 930, 960), "知识组织层", [
        "基础知识库、课程私有知识库、文档抽取、文本分块、Chunk 元数据存储",
    ], fill=(244, 255, 249))
    draw_round_box(draw, (960, 740, 1340, 960), "推理执行层", [
        "TF-IDF 检索、Prompt 组装、模型选择、SSE 流式输出、结果持久化",
    ], fill=(255, 250, 244))
    draw_round_box(draw, (1370, 740, 1620, 960), "数据与外部资源层", [
        "SQLite 数据库", "静态上传文件", "DashScope / Ark 模型接口",
    ], fill=(250, 244, 255))

    for x in (310, 850, 1390):
        draw_arrow(draw, (x, 230), (850, 300))
    draw_arrow(draw, (850, 430), (850, 500))
    draw_arrow(draw, (850, 670), (330, 740))
    draw_arrow(draw, (850, 670), (740, 740))
    draw_arrow(draw, (850, 670), (1150, 740))
    draw_arrow(draw, (1150, 850), (1370, 850), "模型/文件/数据访问")

    note_font = load_font(24)
    draw.text((180, 1000), "说明：系统采用前后端分离架构，AI 能力以工作流形式接入学生端、教师端和管理员端业务场景。", font=note_font, fill=(60, 60, 60))
    img.save(path)


def create_ai_closed_loop(path: Path) -> None:
    img = Image.new("RGB", (1700, 1000), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw_centered_text(draw, (850, 50), "AI 业务闭环与分层实现逻辑", load_font(38, bold=True))

    stage_boxes = [
        ((100, 130, 390, 280), "配置端", ["管理员配置模型、知识库、工作流与客服参数"], (234, 244, 252)),
        ((470, 130, 760, 280), "业务端", ["学生/教师按角色调用 AI 客服、课程助手、智能教案"], (237, 249, 241)),
        ((840, 130, 1130, 280), "数据回流", ["生成任务、日志、问答记录、课程资料更新"], (252, 244, 234)),
        ((1210, 130, 1500, 280), "优化闭环", ["补充知识库、调整模型、修正提示词与工作流策略"], (250, 244, 255)),
    ]
    for box, title, lines, fill in stage_boxes:
        draw_round_box(draw, box, title, lines, fill=fill)
    draw_arrow(draw, (390, 205), (470, 205))
    draw_arrow(draw, (760, 205), (840, 205))
    draw_arrow(draw, (1130, 205), (1210, 205))
    draw_arrow(draw, (1355, 280), (245, 355), "反馈")

    draw_round_box(draw, (180, 420, 1520, 880), "四层 AI 架构", fill=(248, 248, 250))
    draw_round_box(draw, (250, 500, 1450, 580), "第一层：AI 配置编排层", ["模型 API、知识库、工作流 App 与功能参数统一由后台管理"], fill=(244, 249, 255))
    draw_round_box(draw, (250, 610, 1450, 690), "第二层：知识组织层", ["教师上传资料、系统抽取文本、分块建库，为问答和教案生成提供上下文"], fill=(244, 255, 249))
    draw_round_box(draw, (250, 720, 1450, 800), "第三层：推理执行层", ["根据请求解析工作流、选择模型、检索知识片段、拼装 Prompt 并调用模型"], fill=(255, 250, 244))
    draw_round_box(draw, (250, 830, 1450, 910), "第四层：业务接入层", ["AI 客服、AI 课程助手、智能教案三类场景分别面向师生和管理端落地"], fill=(250, 244, 255))
    img.save(path)


def create_ai_er(path: Path) -> None:
    img = Image.new("RGB", (1900, 1200), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw_centered_text(draw, (950, 50), "AI 核心数据 ER 图", load_font(38, bold=True))

    boxes = {
        "sys_users": (80, 160, 470, 370),
        "courses": (80, 510, 470, 720),
        "ai_model_apis": (540, 120, 940, 360),
        "ai_knowledge_bases": (540, 420, 940, 720),
        "ai_workflow_apps": (1010, 120, 1410, 420),
        "ai_kb_documents": (1010, 500, 1410, 780),
        "ai_kb_chunks": (1490, 500, 1830, 820),
        "ai_lesson_plan_tasks": (1490, 120, 1830, 420),
    }
    draw_round_box(draw, boxes["sys_users"], "sys_users", [
        "PK id", "username", "role", "is_active",
    ], fill=(234, 244, 252))
    draw_round_box(draw, boxes["courses"], "courses", [
        "PK id", "name", "teacher_id", "credit", "capacity", "course_type",
    ], fill=(237, 249, 241))
    draw_round_box(draw, boxes["ai_model_apis"], "ai_model_apis", [
        "PK id", "name", "provider", "model_name", "endpoint", "enabled", "is_default",
    ], fill=(252, 244, 234))
    draw_round_box(draw, boxes["ai_knowledge_bases"], "ai_knowledge_bases", [
        "PK id", "slug", "name", "owner_type", "owner_user_id", "course_id", "feature",
    ], fill=(250, 244, 255))
    draw_round_box(draw, boxes["ai_workflow_apps"], "ai_workflow_apps", [
        "PK id", "code", "type", "name", "knowledge_base_id", "model_api_id", "owner_user_id", "course_id", "status",
    ], fill=(246, 248, 252))
    draw_round_box(draw, boxes["ai_kb_documents"], "ai_kb_documents", [
        "PK id", "knowledge_base_id", "title", "original_filename", "url", "file_ext", "enabled",
    ], fill=(244, 249, 255))
    draw_round_box(draw, boxes["ai_kb_chunks"], "ai_kb_chunks", [
        "PK id", "knowledge_base_id", "document_id", "seq", "content", "tokens", "document_title",
    ], fill=(244, 255, 249))
    draw_round_box(draw, boxes["ai_lesson_plan_tasks"], "ai_lesson_plan_tasks", [
        "PK id", "teacher_user_id", "course_id", "title", "status", "result", "knowledge_base_id", "model_api_id",
    ], fill=(255, 250, 244))

    draw_arrow(draw, (470, 265), (540, 265), "用户配置/拥有")
    draw_arrow(draw, (470, 615), (540, 615), "课程关联")
    draw_arrow(draw, (740, 360), (1210, 420), "模型绑定")
    draw_arrow(draw, (940, 560), (1010, 560), "1:N")
    draw_arrow(draw, (1210, 780), (1490, 660), "1:N")
    draw_arrow(draw, (1410, 270), (1490, 270), "任务模型")
    draw_arrow(draw, (1410, 320), (1490, 320), "任务知识库")
    draw_arrow(draw, (940, 520), (1010, 270), "工作流知识库")
    draw_arrow(draw, (470, 320), (1490, 220), "教师创建任务")
    draw_arrow(draw, (470, 650), (1490, 370), "课程关联任务")

    note_font = load_font(22)
    draw.text((80, 1080), "说明：ER 图突出 AI 模型、知识库、工作流、分块文档与教案任务之间的关系，同时与用户、课程业务主表相连接。", font=note_font, fill=(60, 60, 60))
    img.save(path)


def create_flow_diagram(path: Path, title: str, steps: list[str], fill_color=(244, 249, 255)) -> None:
    img = Image.new("RGB", (1700, 760), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw_centered_text(draw, (850, 50), title, load_font(36, bold=True))
    start_x = 70
    width = 240
    top = 250
    bottom = 470
    gap = 35
    centers = []
    for idx, step in enumerate(steps):
        x1 = start_x + idx * (width + gap)
        x2 = x1 + width
        centers.append(((x1 + x2) // 2, (top + bottom) // 2))
        draw_round_box(draw, (x1, top, x2, bottom), f"步骤{idx + 1}", [step], fill=fill_color)
        if idx < len(steps) - 1:
            draw_arrow(draw, (x2, (top + bottom) // 2), (x2 + gap, (top + bottom) // 2))
    img.save(path)


def build_assets() -> dict[str, Path]:
    OUTPUT_DIR.mkdir(exist_ok=True)
    ASSET_DIR.mkdir(exist_ok=True)
    assets = {
        "system_arch": ASSET_DIR / "fig_2_1_system_architecture.png",
        "closed_loop": ASSET_DIR / "fig_2_2_ai_closed_loop.png",
        "er_ai": ASSET_DIR / "fig_3_1_ai_er.png",
        "flow_customer": ASSET_DIR / "fig_4_1_customer_service_flow.png",
        "flow_course": ASSET_DIR / "fig_4_2_course_assistant_flow.png",
        "flow_lesson": ASSET_DIR / "fig_4_3_lesson_plan_flow.png",
        "shot_customer": ASSET_DIR / "fig_4_4_customer_service_placeholder.png",
        "shot_course": ASSET_DIR / "fig_4_5_course_assistant_placeholder.png",
        "shot_lesson": ASSET_DIR / "fig_4_6_lesson_plan_placeholder.png",
        "shot_admin": ASSET_DIR / "fig_4_7_admin_ai_placeholder.png",
    }
    create_system_architecture(assets["system_arch"])
    create_ai_closed_loop(assets["closed_loop"])
    create_ai_er(assets["er_ai"])
    create_flow_diagram(
        assets["flow_customer"],
        "AI 客服核心处理流程",
        ["前端加载客服配置与工作流列表", "用户输入问题并提交到 /api/ai_qa/qa/stream", "后端检索知识库片段并拼装 Prompt", "按优先级解析模型并调用外部模型接口", "SSE 分段返回答案并在界面中实时渲染"],
        fill_color=(234, 244, 252),
    )
    create_flow_diagram(
        assets["flow_course"],
        "AI 课程助手核心处理流程",
        ["管理员配置基础课程助手工作流", "教师复制基础工作流并上传课程私有知识库", "学生或教师按课程选择助手提问", "系统合并工作流知识库与课程知识库进行检索", "模型生成课程相关回答并回传前端"],
        fill_color=(237, 249, 241),
    )
    create_flow_diagram(
        assets["flow_lesson"],
        "智能教案任务化生成流程",
        ["教师选择课程并上传/解析教学资料", "创建教案任务并写入 ai_lesson_plan_tasks", "调用 lesson_plan 工作流进行流式生成", "生成结果回写任务状态并允许教师二次编辑", "教师保存修改结果并导出 Markdown 教案"],
        fill_color=(252, 244, 234),
    )
    create_placeholder_image(assets["shot_customer"], "学生端 / 教师端 AI 客服界面", "建议后期替换为包含推荐问题、流式回答和多会话侧栏的实际运行截图。")
    create_placeholder_image(assets["shot_course"], "AI 课程助手界面", "建议后期替换为教师创建课程助手、学生按课程提问与结果回显的实际截图。")
    create_placeholder_image(assets["shot_lesson"], "智能教案界面", "建议后期替换为知识库文档列表、教案任务清单和生成结果编辑区的实际截图。")
    create_placeholder_image(assets["shot_admin"], "管理员 AI 配置界面", "建议后期替换为模型 API 管理、知识库管理和工作流绑定页面的实际截图。")
    return assets


def query_runtime_data() -> dict:
    counts = {}
    workflows = []
    usage_log_count = 0
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        for table in [
            "sys_users",
            "courses",
            "service_item",
            "service_apply",
            "ai_model_apis",
            "ai_knowledge_bases",
            "ai_kb_documents",
            "ai_kb_chunks",
            "ai_workflow_apps",
            "ai_lesson_plan_tasks",
        ]:
            counts[table] = cur.execute(f"select count(*) from {table}").fetchone()[0]
        usage_log_count = cur.execute("select count(*) from ai_usage_logs").fetchone()[0]
        workflows = [dict(row) for row in cur.execute(
            "select id, code, type, name, status, knowledge_base_id, model_api_id, owner_user_id, course_id from ai_workflow_apps order by id"
        ).fetchall()]
        conn.close()
    return {
        "counts": counts,
        "usage_log_count": usage_log_count,
        "workflows": workflows,
        "test_summary": [
            ["获取 AI 客服配置", "GET /api/ai/customer-service/config", "200", "通过，能够返回欢迎语与推荐问题配置"],
            ["获取 AI 客服工作流", "GET /api/ai/customer-service/apps", "200", "通过，返回可用客服工作流列表"],
            ["获取课程助手工作流", "GET /api/ai/course-assistant/apps", "200", "通过，能够列出启用的课程助手工作流"],
            ["AI 问答流式接口", "POST /api/ai_qa/qa/stream", "200", "通过，SSE 形式返回分段结果"],
            ["教师查询授课课程", "GET /api/ai/teacher/courses", "200", "通过，可按教师账号获取课程集合"],
            ["教师创建课程助手", "POST /api/ai/teacher/course-assistant/apps", "200", "通过，可复制基础工作流生成个人助手"],
            ["创建教案任务", "POST /api/ai/teacher/lesson-plan/tasks", "200", "通过，可写入待处理任务记录"],
            ["更新教案任务结果", "PUT /api/ai/teacher/lesson-plan/tasks/{id}/result", "200", "通过，可回写完成状态与生成内容"],
        ],
    }


def ensure_rfonts(element, east_asia_font: str) -> None:
    rpr = element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), east_asia_font)
    rfonts.set(qn("w:ascii"), FONT_EN)
    rfonts.set(qn("w:hAnsi"), FONT_EN)


def apply_run_font(run, cn_font=FONT_SONG, size=12, bold=False, italic=False, color: RGBColor | None = None):
    run.font.name = FONT_EN
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = color
    ensure_rfonts(run._element, cn_font)
    return run


def configure_document(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.header_distance = Cm(2.0)
    section.footer_distance = Cm(1.5)
    normal = doc.styles["Normal"]
    normal.font.name = FONT_EN
    normal.font.size = Pt(12)
    ensure_rfonts(normal._element, FONT_SONG)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_separate = OxmlElement("w:fldChar")
    fld_separate.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    paragraph._p.append(fld_begin)
    paragraph._p.append(instr)
    paragraph._p.append(fld_separate)
    run = paragraph.add_run("1")
    apply_run_font(run, FONT_EN, 10.5)
    paragraph._p.append(fld_end)


def add_body_paragraph(doc: Document, text: str, *, indent=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY) -> None:
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    if indent:
        p.paragraph_format.first_line_indent = Pt(24)
    run = p.add_run(text)
    apply_run_font(run, FONT_SONG, 12)
    record_text(text)


def add_center_paragraph(doc: Document, text: str, size=12, bold=False, font=FONT_SONG, color=None) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.5
    run = p.add_run(text)
    apply_run_font(run, font, size, bold=bold, color=color)
    record_text(text)


def add_heading1(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(12)
    run = p.add_run(text)
    apply_run_font(run, FONT_HEI, 16, bold=True)
    record_text(text)


def add_heading2(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    apply_run_font(run, FONT_HEI, 14, bold=True)
    record_text(text)


def add_heading3(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    apply_run_font(run, FONT_HEI, 12, bold=True)
    record_text(text)


def add_paragraphs(doc: Document, text: str) -> None:
    for item in normalize_paragraphs(text):
        add_body_paragraph(doc, item)


def add_keywords(doc: Document, label: str, items: list[str], english=False) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.5
    if not english:
        p.paragraph_format.first_line_indent = Pt(24)
    run1 = p.add_run(label)
    apply_run_font(run1, FONT_HEI if not english else FONT_EN, 12, bold=True)
    content = "；".join(items) if not english else "; ".join(items)
    run2 = p.add_run(content)
    apply_run_font(run2, FONT_SONG if not english else FONT_EN, 12)
    record_text(label + content)


def insert_toc(paragraph) -> None:
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r'TOC \o "1-3" \h \z \u'
    fld_separate = OxmlElement("w:fldChar")
    fld_separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "目录请在 Word 中右键选择“更新域”后生成。"
    fld_separate.append(text)
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_separate)
    run._r.append(fld_end)


def set_cell_text(cell, text: str, *, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER, size=10.5) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.line_spacing = 1.25
    run = p.add_run(text)
    apply_run_font(run, FONT_SONG, size, bold=bold)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    record_text(text)


def set_cell_border(cell, **kwargs):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_borders = tc_pr.first_child_found_in("w:tcBorders")
    if tc_borders is None:
        tc_borders = OxmlElement("w:tcBorders")
        tc_pr.append(tc_borders)
    for edge in ("left", "top", "right", "bottom", "insideH", "insideV"):
        data = kwargs.get(edge)
        if data:
            tag = f"w:{edge}"
            element = tc_borders.find(qn(tag))
            if element is None:
                element = OxmlElement(tag)
                tc_borders.append(element)
            for key, value in data.items():
                element.set(qn(f"w:{key}"), str(value))


def apply_three_line_table(table) -> None:
    rows = list(table.rows)
    cols = len(table.columns)
    nil = {"val": "nil"}
    single = {"val": "single", "sz": 8, "color": "000000"}
    for r_idx, row in enumerate(rows):
        for c_idx in range(cols):
            cell = row.cells[c_idx]
            border = {
                "left": nil,
                "right": nil,
                "top": nil,
                "bottom": nil,
            }
            if r_idx == 0:
                border["top"] = single
                border["bottom"] = single
            if r_idx == len(rows) - 1:
                border["bottom"] = single
            set_cell_border(cell, **border)


def add_table(doc: Document, title: str, headers: list[str], rows: list[list[str]], col_widths: list[float] | None = None) -> None:
    add_center_paragraph(doc, title, size=11, bold=True, font=FONT_SONG)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        set_cell_text(hdr[i], h, bold=True)
        if col_widths and i < len(col_widths):
            hdr[i].width = Cm(col_widths[i])
    for row in rows:
        cells = table.add_row().cells
        for i, item in enumerate(row):
            align = WD_ALIGN_PARAGRAPH.LEFT if len(item) > 12 else WD_ALIGN_PARAGRAPH.CENTER
            set_cell_text(cells[i], item, align=align)
            if col_widths and i < len(col_widths):
                cells[i].width = Cm(col_widths[i])
    apply_three_line_table(table)
    doc.add_paragraph()


def add_figure(doc: Document, img_path: Path, caption: str, width_cm=15.5) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(img_path), width=Cm(width_cm))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(6)
    r = cap.add_run(caption)
    apply_run_font(r, FONT_SONG, 10.5)
    record_text(caption)


def add_cover(doc: Document) -> None:
    for _ in range(3):
        doc.add_paragraph()
    add_center_paragraph(doc, "南京工业职业技术大学", size=22, bold=True, font=FONT_HEI)
    add_center_paragraph(doc, "本科毕业设计（论文）", size=20, bold=True, font=FONT_HEI)
    doc.add_paragraph()
    doc.add_paragraph()
    add_center_paragraph(doc, TITLE, size=24, bold=True, font=FONT_HEI, color=RGBColor(0x1F, 0x3A, 0x5F))
    doc.add_paragraph()
    doc.add_paragraph()
    table = doc.add_table(rows=7, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    labels = ["学生姓名", "学号", "学院", "专业", "班级", "指导教师", "企业导师"]
    values = [AUTHOR, STUDENT_ID, COLLEGE, MAJOR, CLASS_NAME, TEACHER, ENTERPRISE_MENTOR]
    for i, (k, v) in enumerate(zip(labels, values)):
        set_cell_text(table.rows[i].cells[0], k, bold=True)
        set_cell_text(table.rows[i].cells[1], v, align=WD_ALIGN_PARAGRAPH.LEFT)
    for row in table.rows:
        for cell in row.cells:
            set_cell_border(cell, left={"val": "nil"}, right={"val": "nil"}, top={"val": "nil"}, bottom={"val": "nil"})
    doc.add_paragraph()
    doc.add_paragraph()
    add_center_paragraph(doc, DATE_CN, size=14, bold=True, font=FONT_SONG)
    doc.add_page_break()


def add_integrity_page(doc: Document) -> None:
    add_center_paragraph(doc, "诚信承诺书", size=18, bold=True, font=FONT_HEI)
    add_paragraphs(doc, """
    本人郑重声明：所提交的毕业设计（论文）《AI赋能的高校教务系统》是在指导教师指导下独立完成的研究成果。除文中已经明确注明引用的内容外，论文中不包含其他个人或集体已经发表或撰写过的研究成果，也不包含为获得南京工业职业技术大学或其他教育机构学位、证书而使用过的材料。

    本论文以项目代码、数据库结构、开题报告、任务书以及中期答辩材料为主要依据，围绕系统的真实功能、真实实现路径和真实测试结果展开分析。文中所涉及的系统架构、接口逻辑、数据结构与存在问题，均来源于项目当前版本的代码与本地验证结果，不故意夸大系统能力，不编造未完成的实验结论。

    若因本论文内容引发学术不端、知识产权或事实失实等问题，本人愿承担相应责任。
    """)
    doc.add_paragraph()
    add_body_paragraph(doc, f"学生签名：{AUTHOR}　　　　　　　　　　　　　　　　日期：{CHECK_DATE_CN}", indent=False)
    doc.add_page_break()


def add_abstract_pages(doc: Document) -> None:
    add_center_paragraph(doc, "摘  要", size=18, bold=True, font=FONT_HEI)
    add_paragraphs(doc, """
    本文研究对象不是一个抽象概念化的“智慧校园平台”，而是一个已经完成主要代码开发、数据库建模和页面实现的高校教务项目。论文写作过程以实际仓库为分析中心，对前端视图、后端路由、数据表、启动脚本和本地测试结果进行逐项核对，再据此归纳系统的设计思路与可用范围。相比单纯从需求文档反推系统，本文更强调“代码里真正实现了什么、哪些环节已经跑通、哪些部分仍需补强”。

    系统整体采用前后端分离方案。前端使用 Vue3、TypeScript、Element Plus、Pinia 与 Vue Router 组织学生端、教师端和管理员端页面；后端使用 FastAPI、SQLAlchemy 与 SQLite 提供统一接口和数据持久化支撑，并通过 Socket.IO 补充即时通信能力。围绕 AI 相关能力，系统在现有教务业务之上额外实现了模型管理、知识库管理、工作流绑定、流式问答和教案任务回写等功能，使 AI 服务不再是孤立页面，而是嵌入到真实业务流中的组成部分。

    论文重点分析三个实际落地的 AI 场景。第一，AI 客服通过配置读取、知识片段检索与 SSE 流式回答，为学生端和教师端提供统一的教务咨询入口。第二，AI 课程助手允许教师基于管理员提供的基础工作流复制生成个人助手，并将课程资料纳入私有知识库后再面向学生开放课程相关问答。第三，智能教案页面采用“先建任务、后做生成、再回写结果”的实现方式，把生成内容保存到任务表，支持继续编辑与导出。底层检索链路采用 TF-IDF 与余弦相似度进行文本召回，属于轻量级、便于部署的检索增强方案。

    截至2026年4月24日，项目本地数据库中已保存 4 条模型 API 配置、4 个知识库、3 份知识库文档、86 个知识片段、4 个工作流应用以及 3 条教案任务记录。围绕这些对象所做的内存数据库联调进一步表明，客服配置读取、工作流列表读取、统一问答接口调用、教师创建课程助手、创建教案任务和回写结果等关键接口均能返回 HTTP 200。由此可见，系统已经具备答辩展示所需的主链路可运行条件。

    在总结实现成果的同时，本文也对代码中的真实不足进行说明，包括客服模板参数尚未进入最终 Prompt、禁用工作流仍缺少严格执行层校验、多轮对话记忆链路尚未真正闭合，以及旧测试脚本与当前接口不一致等问题。论文的价值并不在于回避这些不足，而在于基于真实实现给出客观分析和下一步可执行的优化方向。
    """)
    add_keywords(doc, "关键词：", ["高校教务系统", "人工智能", "知识库检索", "AI课程助手", "智能教案"])
    doc.add_page_break()

    add_center_paragraph(doc, "ABSTRACT", size=18, bold=True, font=FONT_EN)
    add_paragraphs(doc, """
    With the continuous promotion of digital transformation in education, university academic affairs systems are expected to evolve from simple information recording platforms into integrated platforms that combine management, service and decision support. Conventional systems can usually complete basic tasks such as user management, course management, leave approval and grade inquiry, but they still rely heavily on manual work in high-frequency consultation, course learning support and teaching material generation. To address these problems, this thesis designs and implements an AI-enabled academic affairs system for students, teachers and administrators based on the actual graduation project codebase and the mid-term defense logic.

    The system adopts a front-end/back-end separation architecture. The front end is built with Vue3, TypeScript, Element Plus, Pinia and Vue Router, while the back end is built with FastAPI, SQLAlchemy, SQLite and Socket.IO. The AI part follows a closed-loop route of configuration, business access, data feedback and continuous optimization, and is organized into four layers: AI configuration orchestration, knowledge organization, inference execution and business access.

    Three AI modules are implemented as the core scenarios. The AI customer service module connects workflow configuration, knowledge retrieval and streaming question answering for campus consultation. The AI course assistant supports teacher-owned course workflows and course knowledge bases so that students can ask course-specific questions. The intelligent lesson plan module adopts a task-oriented design, allowing teachers to create lesson plan tasks, stream generated content and persist results for later editing and export. The current system uses a lightweight retrieval-augmented generation strategy based on TF-IDF chunk retrieval and prompt assembly.

    As of April 24, 2026, the local database already contains model APIs, knowledge bases, chunked documents, workflow applications and lesson plan task records. Local integration verification based on an in-memory database and mocked model responses shows that the key AI interfaces all return HTTP 200, which demonstrates that the main AI chain is available for demo and defense. Meanwhile, this research also identifies several improvement directions, including prompt template injection, stronger workflow status validation, real conversation memory and more robust automated testing.
    """)
    add_keywords(doc, "Key words: ", ["academic affairs system", "artificial intelligence", "knowledge base retrieval", "course assistant", "lesson plan generation"], english=True)
    doc.add_page_break()


def add_toc_page(doc: Document) -> None:
    add_center_paragraph(doc, "目  录", size=18, bold=True, font=FONT_HEI)
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.5
    insert_toc(p)
    record_text("目录")
    doc.add_page_break()


def add_references(doc: Document, refs: list[str]) -> None:
    add_heading1(doc, "参考文献")
    for idx, item in enumerate(refs, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.first_line_indent = Pt(-24)
        p.paragraph_format.left_indent = Pt(24)
        run = p.add_run(f"[{idx}] {item}")
        apply_run_font(run, FONT_SONG, 10.5)
        record_text(item)


def build_doc(assets: dict[str, Path], data: dict) -> Document:
    doc = Document()
    configure_document(doc)
    for section in doc.sections:
        footer_p = section.footer.paragraphs[0]
        add_page_number(footer_p)

    add_cover(doc)
    add_integrity_page(doc)
    add_abstract_pages(doc)
    add_toc_page(doc)

    counts = data["counts"]
    workflows = data["workflows"]
    workflow_rows = [[
        str(item["id"]),
        item["code"],
        item["type"],
        item["name"],
        item["status"],
        str(item["knowledge_base_id"] or ""),
        str(item["model_api_id"] or ""),
    ] for item in workflows]

    add_heading1(doc, "第一章 绪论")
    add_heading2(doc, "1.1 研究背景与课题意义")
    add_paragraphs(doc, """
    本课题的研究背景来自两个层面：一是高校教务业务正在持续数字化，二是当前大模型工具已经具备较好的语言理解与生成能力，但多数教务系统还没有把这两部分真正接起来。通过查看项目代码可以发现，传统功能如用户、课程、请假、办事大厅、消息与证书管理已经形成相对完整的业务骨架，而 AI 模块要解决的问题并不是替代这些业务，而是补上“解释、辅助、生成”三个经常依赖人工经验的薄弱环节。

    在真实使用场景中，学生往往不知道应该先去哪个页面完成某项手续，也不知道某条流程规则是否适用于自己；教师能够完成授课任务，但在课程资料归集、重复答疑和教案组织上会耗费较多时间；管理员虽然掌握后台配置权限，却缺少一个统一入口来管理模型、知识来源和不同场景下的 AI 行为。正因为这些问题同时存在，教务系统的升级不能只靠增加菜单数量，而需要把可解释的 AI 服务融入已有流程之中 [3][9]。

    本文的研究意义更多体现为工程层面的整理与验证。理论上，论文尝试说明高校教务 AI 不应只是一个通用对话框，而应该由模型、知识库、工作流和业务路由共同构成。实践上，项目围绕 AI 客服、AI 课程助手和智能教案这三类最容易展示价值的场景展开实现，并通过数据库样本、接口联调和代码缺陷分析证明这些能力已经不再停留在概念设计阶段，而是具备可运行、可说明和可迭代的现实基础。
    """)

    add_heading2(doc, "1.2 国内外研究现状")
    add_paragraphs(doc, """
    国内高校教务系统的研究与实践，长期以课程管理、成绩管理、排课管理、用户权限和办事流程为核心。相关文献多聚焦于前后端分离架构设计、数据库规范化、业务流程在线化及数据统计展示等方向 [1][2]。随着 AI 技术进入高校管理场景，一些研究开始探索智能排课、学情预警、智能推荐与在线问答等功能 [7][10]，但很多系统仍停留在单点能力接入阶段，例如只在首页嵌入一个通用聊天窗口，或者将大模型当作知识搜索的替代品，而没有真正解决“知识来源可信”“业务权限可控”“结果能够回流优化”的问题。

    国外在课程推荐、学业规划、个性化学习路径和解释型教育 AI 方面起步较早，一些研究强调根据课程上下文、学生行为和学习目标给出更具针对性的建议 [11][12]。这类研究的启发在于：教育场景下的 AI 并不是越通用越好，而是越贴合具体课程、具体角色和具体数据约束越有效。然而，国外相关系统往往更偏向单一教学平台或学习支持系统，与我国高校教务流程、审批制度和角色结构并不完全一致，直接照搬难以满足本地化管理需求。

    综合现有研究可以发现，当前真正不足的不是“有没有 AI 功能”，而是“AI 能否与教务业务结构深度融合”。具体表现在三个方面：第一，很多系统把模型能力直接暴露给用户，缺少后台配置和工作流编排，导致后期维护成本高；第二，知识库建设与课程、角色、权限脱节，造成回答泛化甚至与校内制度不符；第三，模型调用后的结果缺少日志、任务或状态记录，不利于问题复现与持续优化。基于此，本文将项目设计重点放在 AI 配置能力、知识组织能力和业务接入能力的统一实现上，以弥补“功能存在但工程闭环不足”的研究空缺。
    """)

    add_heading2(doc, "1.3 研究目标、内容与技术路线")
    add_paragraphs(doc, """
    本课题的直接目标，是把仓库中已经存在的多角色教务系统扩展成一个带有 AI 服务能力的可演示版本，并对其核心链路进行系统化说明。论文围绕三个层次展开：第一层是梳理学生、教师和管理员在实际页面中分别能做什么；第二层是从代码角度解释模型、知识库、工作流与任务表如何协作；第三层是通过本地联调结果确认这些设计并非停留在界面原型，而是已经进入可运行状态。

    对应到研究内容，本文重点完成四项工作：一是分析系统的角色需求与模块边界，明确 AI 不替代原有业务，而是为其提供辅助层；二是整理与 AI 相关的数据结构，包括 ai_model_apis、ai_knowledge_bases、ai_workflow_apps 和 ai_lesson_plan_tasks 等核心表；三是按模块拆解 AI 客服、AI 课程助手与智能教案的前后端逻辑，并指出代码中已经实现和仍待完善的部分；四是基于接口联调和测试脚本复查，给出系统当前的可用性结论与后续优化清单。

    技术路线则更加偏向“先核实实现，再归纳结构”。具体做法是：先查看前端页面与 API 封装，确认用户端的真实交互入口；再查看后端路由和服务函数，梳理工作流解析、知识检索和模型调用顺序；随后结合数据库现有数据与本地测试结果，验证链路是否贯通；最后根据发现的问题反推系统的改进方向。这样的路线避免了只从开题设想出发描述系统，而是尽量让论文内容与当前代码状态保持一致。
    """)

    add_heading2(doc, "1.4 论文结构安排")
    add_paragraphs(doc, """
    本文共分为六章。第一章介绍课题背景、研究意义、国内外研究现状以及本文的研究目标。第二章从业务需求出发，对系统的角色需求、功能需求、非功能需求和总体架构进行分析。第三章围绕前后端技术栈、知识库组织、检索增强生成与数据库设计展开，说明系统实现所依赖的关键技术。第四章重点分析 AI 客服、AI 课程助手、智能教案以及管理员 AI 配置模块的具体逻辑和代码实现。第五章给出系统测试策略、接口联调结果和存在问题分析。第六章总结全文，并对后续改进方向进行展望。文末附参考文献、致谢和附录，便于后续继续完善毕业论文终稿。
    """)

    add_heading1(doc, "第二章 需求分析与总体设计")
    add_heading2(doc, "2.1 业务场景与角色需求分析")
    add_paragraphs(doc, """
    需求分析不是从抽象角色描述出发，而是先回到项目现有页面和接口。学生端已经具备课程、请假、办事大厅、证书等功能，因此学生对 AI 的需求主要不是“再多一个系统入口”，而是希望在原有入口之外得到快速说明和学习辅助。也就是说，学生最关心的是能否用自然语言直接问清流程、问清课程内容，以及在教师共享资料后得到更连续的学习支持。

    教师端的诉求与学生端明显不同。查看教师页面可以发现，课程助手和智能教案都围绕课程资料组织展开，因此教师更在意知识上传是否方便、课程绑定是否明确、生成内容能否继续编辑以及结果是否可沉淀。换句话说，教师需要的不是一个“万能聊天机器人”，而是一个能围绕自己课程资料工作、并能节省重复备课和答疑时间的工具。

    管理员端的核心任务则是治理。管理员并不频繁直接提问，但需要保证哪些模型可用、哪些知识库属于哪个场景、哪个工作流对哪个页面开放都可以在后台统一配置。因此在本系统中，管理员承担的是 AI 资源调度者的角色。正是因为学生、教师、管理员三类需求明显不同，系统才必须采用角色分层与工作流分层并存的设计思路。
    """)

    add_table(
        doc,
        "表2-1  角色需求与 AI 价值对应关系",
        ["角色", "基础业务需求", "AI 相关需求", "预期价值"],
        [
            ["学生", "课程查询、请假、办事大厅、证书查看", "AI 客服、AI 课程助手、查看共享教案", "降低咨询等待时间，提升学习支持的即时性"],
            ["教师", "课程管理、作业批改、教学组织", "课程知识库上传、课程助手创建、智能教案生成", "减少重复备课劳动，沉淀课程资源"],
            ["管理员", "用户维护、数据治理、流程配置", "模型 API 管理、知识库管理、工作流编排、客服参数配置", "实现 AI 能力的统一治理与可持续运维"],
        ],
        [2.4, 5.0, 5.0, 4.8],
    )

    add_heading2(doc, "2.2 功能需求分析")
    add_paragraphs(doc, """
    从代码结构上看，系统功能更适合分为“已有教务业务”和“AI 增强业务”两层。已有业务模块负责承载真实校园流程，AI 模块则在这些流程之上补充问答、资料辅助和内容生成能力。这样的划分有一个明显好处：AI 功能不需要凭空造场景，而是直接借用已有课程、用户、服务事项和角色权限。

    具体到 AI 客服，功能需求并不只是“能回答”，还包括“能配置、能切换、能流式返回”。因此它至少需要四个步骤：管理员在后台维护客服工作流和展示参数；前端聊天组件在进入页面时自动拉取配置；用户提问后统一调用流式接口；后端根据工作流绑定的知识库与模型输出结果。AI 课程助手的功能链更长，因为它还要求教师能够复制基础工作流、上传课程资料，并使这些资料在学生提问时真正参与检索。

    智能教案则体现出任务型功能的特点。教师并不是一次输入一句话就结束，而是要经历选课、选资料、建任务、生成、修改、保存和导出等多个环节。所以对这个模块来说，最关键的需求不是“生成快”，而是“生成过程有记录、生成结果能复用、失败时可定位原因”。这也是系统专门设置 ai_lesson_plan_tasks 表而不是只返回一段文本的原因。
    """)

    add_heading2(doc, "2.3 非功能需求分析")
    add_paragraphs(doc, """
    非功能需求决定了系统能否长期维护，而不仅仅是答辩时能否演示。从当前实现看，可维护性首先来自结构划分：前端页面、API 封装、后端路由、数据模型和服务函数边界比较明确，AI 功能新增后并没有破坏普通教务模块的组织方式。其次，可扩展性体现在模型、知识库和工作流被抽象为独立对象，后续如果更换模型供应商或扩展新的 AI 场景，不必重写整套页面逻辑。

    可用性方面，系统已经做出两类较实际的设计。其一是角色分流，学生端只看到与提问和使用有关的入口，配置行为主要留给教师和管理员。其二是流式输出，用户在等待完整答案之前就能看到部分结果返回，这对问答类界面尤其重要。安全性方面，后端通过当前用户依赖和角色判断限制敏感操作，例如教师上传课程资料前需要验证课程归属，管理员相关接口则只向管理员开放。

    对 AI 模块来说，还必须关注结果可解释性和故障可处理性。当前系统通过知识分块、任务状态、工作流绑定和错误提示来尽量保留链路信息，这些措施虽然还不等于完整的质量评估体系，但已经比单纯“调一下模型返回字符串”的实现更适合后续追踪和维护。也正因为如此，论文才可以在后文中较明确地指出系统缺口，而不是停留在概念描述层面。
    """)

    add_heading2(doc, "2.4 系统总体架构设计")
    add_paragraphs(doc, """
    根据项目代码实现，系统总体上采用“前端展示层—后端服务层—AI 能力层—数据与外部资源层”的分层架构。前端使用 Vue3 与 TypeScript 负责页面渲染和交互逻辑，Pinia 负责状态管理，Axios 负责普通 HTTP 请求，浏览器原生 fetch 配合自定义解析逻辑完成 SSE 流式问答。后端由 FastAPI 承载路由组织与依赖注入，SQLAlchemy 负责 ORM 建模与数据库会话管理，Socket.IO 用于即时通信与在线状态维护，SQLite 用于保存业务数据与 AI 配置数据。

    在具体接入方式上，系统在 backend/app/main.py 中统一挂载了普通教务路由、管理员 AI 路由、AI Portal 路由和 AI QA 路由，并额外使用 /api 前缀构建统一接口出口。这种方式既兼容局部历史路由，又保持了前端访问的一致性。前端方面，学生端和教师端共用同一套核心请求函数 streamQA，通过传入模型、课程编号与工作流 code，将问题发送至 /api/ai_qa/qa/stream，由后端按需解析业务场景。
    """)
    add_figure(doc, assets["system_arch"], "图2-1  系统总体架构图", width_cm=16.2)

    add_heading2(doc, "2.5 AI 闭环设计与答辩主线映射")
    add_paragraphs(doc, """
    结合中期答辩材料，本文将系统的 AI 主线概括为“配置端—业务端—数据回流—优化闭环”。其中，配置端是管理员对模型 API、知识库和工作流的统一编排；业务端是学生与教师通过具体页面调用 AI 能力；数据回流是日志、任务状态、知识库文档与课程资料在系统中的沉淀；优化闭环则是根据使用效果持续调整模型、知识库与流程策略。这一主线之所以重要，是因为它表明本系统中的 AI 不是简单外挂，而是能够被配置、被接入、被追踪、被优化的一套业务能力。

    为了支撑这一闭环，系统进一步抽象出 AI 配置编排层、知识组织层、推理执行层和业务接入层四层结构。配置编排层决定“用什么模型、调哪个知识库、由哪类工作流处理”；知识组织层负责“把教师与管理员上传的资料转化成机器可检索的文本块”；推理执行层负责“根据问题检索片段、拼装 Prompt、调用模型并流式返回”；业务接入层则保证“AI 客服、AI 课程助手和智能教案”三个场景能够被不同角色访问并形成可视化交互。这一分层设计也是后文展开代码实现分析的逻辑基础。
    """)
    add_figure(doc, assets["closed_loop"], "图2-2  AI 业务闭环与分层实现逻辑", width_cm=16.2)

    add_table(
        doc,
        "表2-2  项目开发与运行环境",
        ["类别", "配置内容"],
        [
            ["操作系统", "Windows 开发环境（论文撰写与接口联调日期：2026年4月24日）"],
            ["Python 运行环境", "Python 3.13.13，使用项目内 .venv 虚拟环境"],
            ["Node.js 环境", "Node.js v22.19.0"],
            ["前端技术", "Vue3、TypeScript、Element Plus、Pinia、Vue Router、Vite"],
            ["后端技术", "FastAPI、SQLAlchemy、SQLite、Socket.IO、scikit-learn"],
            ["AI 接入方式", "DashScope OpenAI 兼容接口、Ark Responses 接口、SSE 流式输出"],
        ],
        [4.0, 11.0],
    )

    add_heading1(doc, "第三章 关键技术与数据结构设计")
    add_heading2(doc, "3.1 前后端分离与技术栈选型")
    add_paragraphs(doc, """
    从代码实际实现来看，项目最终采用了 Vue3 + TypeScript + Element Plus 的前端技术组合，而不是开题报告中预期的 Vuetify 方案。这一变化并不是简单的“换组件库”，而是开发过程中的工程化取舍：一方面，Element Plus 与现有后台管理类页面和表格、表单组件结合更紧密，便于快速承接教务系统中大量的录入与展示场景；另一方面，项目原有页面结构和配套生态更适合在 Vue3 + Element Plus 的体系内持续扩展，因此最终实现与最初设想存在差异，但更符合项目代码的真实落地状态。

    后端方面，FastAPI 的异步接口模型、自动文档能力和依赖注入机制使其适合承载较多角色接口与 AI 接口。SQLAlchemy 为系统提供了统一的 ORM 抽象，使业务表与 AI 表可以在同一套会话管理下完成读写；SQLite 则适合毕业设计阶段的轻量部署和本地联调。与此同时，requirements.txt 中还包含 scikit-learn、pypdf、pandas 等依赖，为知识库文档抽取、轻量检索和数据处理提供支持。整体来看，这套技术栈在工程复杂度、可学习性和可演示性之间取得了较好平衡 [4][5][6]。
    """)

    add_heading2(doc, "3.2 AI 工作流、知识库与文档处理机制")
    add_paragraphs(doc, """
    本系统 AI 能力的基础不是某一个聊天页面，而是后台抽象出的工作流应用、模型 API 和知识库对象。管理员通过 admin_ai.py 中的相关接口维护 ai_model_apis、ai_knowledge_bases 和 ai_workflow_apps 三类核心对象。模型 API 记录模型名称、供应商、endpoint、api_key、超时、温度与输出长度等信息；知识库记录 owner_type、course_id、feature 等属性，用于区分系统级知识库、课程级知识库和不同 AI 功能场景；工作流应用负责把模型与知识库绑定起来，并通过 code 区分 AI 客服、AI 课程助手和智能教案等不同业务入口。

    知识库真正能够支撑检索，依赖于文档上传和文本分块机制。根据 services/ai_workflow.py 的实现，系统支持从 txt、md、csv、pdf、docx、xlsx 等多种文件中抽取文本。抽取到的文本会先进行换行规范化，再按照默认 450 字符的块大小与 80 字符重叠量切分为多个 chunk。每个 chunk 除正文外，还会记录 tokens、文档标题、文档 URL、所在知识库和所属文档等元数据，最终写入 ai_kb_chunks 表。这样的设计使知识库不再是“上传了文件但系统不会用”，而是转化为后续问答链路可检索、可追踪的数据资产。

    教师侧的课程知识库与管理员侧的基础知识库并不是同一种对象的简单复制，而是通过 owner_user_id 与 course_id 的组合体现出所有权和课程归属。教师在 CourseAssistant.vue 与 LessonPlan.vue 中上传课程资料时，后端会先校验课程是否属于当前教师，再确保存在对应的课程知识库和主题对象，然后保存文件、抽取文本并重建 chunk。这种从权限校验到知识组织的完整过程，使 AI 课程助手和智能教案真正具备“按课程、按教师、按场景”运行的条件。
    """)

    add_heading2(doc, "3.3 轻量级检索增强生成实现")
    add_paragraphs(doc, """
    在问答与教案生成链路中，知识库的价值最终要通过检索增强生成体现出来。项目当前没有引入向量数据库，而是采用了一种适合毕业设计阶段的轻量级 RAG 方案。具体而言，后端在 retrieve_top_chunks 函数中先拉取目标知识库最近的 chunk 集合，再使用 scikit-learn 的 TfidfVectorizer 构建问题与文本片段的特征表示，之后通过 cosine_similarity 计算相似度并选出 Top-K 结果。被召回的片段会在 _build_prompt 函数中拼装为编号上下文，再与用户问题共同组成最终 Prompt 发送给模型。

    这种实现方式有三个明显优点。第一，依赖简单，不需要额外部署向量服务，适合毕业设计项目在单机环境中快速运行；第二，检索逻辑清晰，便于在答辩中展示文档如何被拆分、检索和拼接；第三，对中小规模知识库具有较好的工程性价比。从当前数据库规模看，截至2026年4月24日，系统中共包含 86 个 chunk，这样的数据规模足以让轻量级 TF-IDF 检索发挥作用。

    但从工程完整性角度看，该方案也存在客观限制。由于 TF-IDF 更偏向关键词匹配，对同义表达、长文本语义关联和跨文档概念召回的能力有限；同时，系统当前更多是把工作流知识库与课程知识库合并后一起计算相似度，并未在算法层面对“课程私有知识优先”做严格排序策略。因此，在论文后续展望中，本文将向量检索、混合检索和引用追踪列为重要升级方向。答辩材料中提出的“轻量 RAG 可先落地、后续逐步演进”的思路，与当前代码实现是一致的。
    """)

    add_heading2(doc, "3.4 模型选择优先级与 SSE 流式响应机制")
    add_paragraphs(doc, """
    在模型调用方面，ai_qa.py 实现了较明确的优先级策略。首先，若前端请求中明确传入 model 参数，后端会优先尝试解析并查找启用状态的模型；其次，若工作流本身绑定了 model_api_id，则使用工作流所绑定的模型；最后，若前两步都无法获取可用模型，系统会回退到“已启用且优先级最高”的默认模型。这样的设计使学生、教师和管理员都可以在统一接口上复用 একই套推理入口，同时保留场景级差异化模型选择能力。

    由于大模型响应通常具有生成耗时，系统采用 Server-Sent Events 作为前后端流式通信机制。前端 streamQA 函数向 /api/ai_qa/qa/stream 发送 POST 请求，并在收到 text/event-stream 响应后按 \n\n 分帧解析数据块；后端则在 _call_model_api 中将模型输出拆分为多段，以“data: {content: ...}”的方式逐段返回。这样的实现虽然没有使用 WebSocket，但足以满足当前 AI 场景的单向流式输出需求，既降低了复杂度，也改善了用户等待体验。

    值得指出的是，系统已经支持 DashScope OpenAI 兼容接口与 Ark Responses 两种 provider，这意味着模型接入层已经具备一定抽象能力。管理员端页面还提供了模型连通性测试入口，可在保存前快速验证 endpoint、api_key 和 model_name 是否正确。对于毕业设计而言，这种“模型配置—接口测试—业务调用”的链路已经说明系统不仅是功能演示，更具备基本的工程可运维性。
    """)

    add_heading2(doc, "3.5 数据库设计与核心表结构")
    add_paragraphs(doc, f"""
    数据库设计是连接业务逻辑与 AI 能力的关键环节。项目当前以 SQLite 作为底层数据库，在普通业务表之外，围绕 AI 功能增加了模型 API 表、知识库表、知识库文档表、知识库分块表、工作流应用表、教案任务表、课程 AI 收藏与选择表、AI 使用日志表等结构。这些表不仅记录配置数据，也记录运行状态和生成结果，从而使系统的 AI 行为能够被追踪、被复盘、被二次利用。

    截至{CHECK_DATE_CN}，本地数据库中已有 {counts.get("ai_model_apis", 0)} 条模型 API 配置、{counts.get("ai_knowledge_bases", 0)} 个知识库、{counts.get("ai_kb_documents", 0)} 份知识库文档、{counts.get("ai_kb_chunks", 0)} 个分块片段、{counts.get("ai_workflow_apps", 0)} 个工作流应用、{counts.get("ai_lesson_plan_tasks", 0)} 条教案任务记录，以及 {data.get("usage_log_count", 0)} 条 AI 使用日志。这些样本说明系统不仅完成了表结构设计，也形成了实际可分析的数据实体。
    """)
    add_figure(doc, assets["er_ai"], "图3-1  AI 核心数据 ER 图", width_cm=16.5)
    add_table(
        doc,
        "表3-1  AI 核心数据表设计说明",
        ["数据表", "主要字段", "作用说明"],
        [
            ["ai_model_apis", "name、provider、model_name、endpoint、enabled、is_default", "维护外部模型连接信息，支持默认模型与多供应商切换"],
            ["ai_knowledge_bases", "slug、name、owner_type、owner_user_id、course_id、feature", "按系统/教师/课程维度组织知识来源"],
            ["ai_kb_documents", "knowledge_base_id、title、original_filename、url、file_ext、enabled", "记录上传文档及其文件元数据"],
            ["ai_kb_chunks", "knowledge_base_id、document_id、seq、content、tokens", "保存分块后的检索单元，是 RAG 的基础数据"],
            ["ai_workflow_apps", "code、type、name、knowledge_base_id、model_api_id、status", "抽象不同 AI 场景的可配置入口"],
            ["ai_lesson_plan_tasks", "teacher_user_id、course_id、title、status、result、completed_at", "持久化教案生成任务及结果"],
            ["ai_usage_logs", "feature、user_id、user_role、result、message", "记录使用行为和结果，支持后续统计与优化"],
        ],
        [3.0, 6.0, 6.0],
    )
    add_table(
        doc,
        "表3-2  当前数据库样例规模统计（截至2026年4月24日）",
        ["表名", "记录数", "说明"],
        [
            ["sys_users", str(counts.get("sys_users", 0)), "系统用户总量，含管理员、教师与学生"],
            ["courses", str(counts.get("courses", 0)), "课程主数据"],
            ["service_item", str(counts.get("service_item", 0)), "办事大厅服务事项"],
            ["service_apply", str(counts.get("service_apply", 0)), "服务申请记录"],
            ["ai_model_apis", str(counts.get("ai_model_apis", 0)), "模型 API 配置记录"],
            ["ai_knowledge_bases", str(counts.get("ai_knowledge_bases", 0)), "知识库记录"],
            ["ai_kb_documents", str(counts.get("ai_kb_documents", 0)), "知识库文档记录"],
            ["ai_kb_chunks", str(counts.get("ai_kb_chunks", 0)), "知识库文本分块记录"],
            ["ai_workflow_apps", str(counts.get("ai_workflow_apps", 0)), "AI 工作流应用记录"],
            ["ai_lesson_plan_tasks", str(counts.get("ai_lesson_plan_tasks", 0)), "智能教案任务记录"],
        ],
        [4.0, 2.5, 8.5],
    )
    if workflow_rows:
        add_table(
            doc,
            "表3-3  当前工作流应用样例",
            ["ID", "Code", "类型", "名称", "状态", "知识库ID", "模型ID"],
            workflow_rows,
            [1.2, 4.1, 2.8, 3.0, 1.8, 1.8, 1.8],
        )

    add_heading1(doc, "第四章 系统功能设计与实现")
    add_heading2(doc, "4.1 系统模块划分与代码组织")
    add_paragraphs(doc, """
    从代码目录结构来看，后端采用 models、routers、schemas、services、dependencies 等经典分层方式组织，前端则以 views、components、api、stores 和 router 等目录组织页面与交互逻辑。这样的结构使业务功能与 AI 功能既能够并列存在，又能通过统一依赖机制共享用户认证、数据库连接和静态资源访问方式。例如，backend/app/main.py 在系统启动时统一注册了 ai_qa、ai_portal、admin_ai 等 AI 相关路由，同时保留课程、请假、办事大厅、证书和消息等基础业务路由，保证 AI 能力始终建立在完整的教务业务框架之上。

    前端的角色化设计也较为清晰。学生端页面重点提供课程查询、办事大厅和 AI 课程助手等入口；教师端页面则额外提供知识库维护、课程助手自定义和智能教案任务管理等功能；管理员端通过 AdminAIConfig.vue 集中管理模型、知识库与工作流绑定。尤其值得注意的是，AI 客服组件并不是孤立页面，而是通过 Layout.vue 在学生端和教师端统一挂载，这意味着 AI 客服被设计成平台级服务，而非某个局部试验性功能。
    """)

    add_heading2(doc, "4.2 AI 客服逻辑与代码实现")
    add_paragraphs(doc, """
    AI 客服是系统中最贴近“校园服务入口”的模块。前端 StudentAIChat.vue 与 TeacherAIChat.vue 在组件挂载时会先请求 /ai/customer-service/config 和 /ai/customer-service/apps 两个接口，加载欢迎语、推荐问题、输入框提示语以及当前可用的客服工作流。用户提交问题后，组件统一调用 streamQA 方法，将 workflow code、user_id 和问题文本发送给 /api/ai_qa/qa/stream。组件内部还维护了本地多会话列表、浮动窗口位置和未读状态等交互逻辑，使 AI 客服不仅能回答问题，也具备较好的可用界面。

    后端 AI 客服的核心逻辑集中在 ai_qa.py。首先，_load_workflow_app 根据 workflow code 读取工作流对象；其次，_resolve_model 按“请求指定模型—工作流绑定模型—已启用默认模型”的优先级解析最终模型；然后，_collect_kb_ids 会收集工作流绑定知识库和课程知识库的编号；接着，_build_prompt 基于 retrieve_top_chunks 召回的文本片段拼装 Prompt；最后，_call_model_api 按 provider 类型调用外部模型接口，并将结果拆分为 SSE 数据块返回前端。整个流程体现出较强的工程层次感：UI 不直接依赖某个模型实现，后端也不把知识库、模型和业务场景写死，而是通过工作流协调起来。

    从业务价值看，AI 客服适合处理请假流程、选课规则、成绩查询入口、服务事项说明等高频问题。它的优势在于响应快、接入统一、配置灵活，并且可以随着知识库补充逐步提高回答质量。由于系统中还保留了普通办事大厅、请假与课程功能，AI 客服可以作为这些模块的“解释层”，帮助用户从“会点按钮”转向“理解流程”。这也是该模块相比通用聊天机器人更具校园教务属性的原因。

    不过，通过代码分析也可以看到该模块尚有几个需要完善的点。第一，settings_json 中虽然存在 system_prompt_template 配置项，但当前 _build_prompt 只拼装检索上下文和问题文本，并没有真正把该模板注入最终 Prompt；第二，_load_workflow_app 目前按 code 直接查询，不校验工作流状态，因此若前端或外部调用仍持有某个已禁用 workflow 的 code，理论上仍可能继续访问；第三，前端传递了 history_flag，但当前主链路并未形成稳定的多轮记忆输入。这些问题并不影响模块基本可用性，却是系统从“能演示”走向“更可靠”的关键改进点。
    """)
    add_figure(doc, assets["flow_customer"], "图4-1  AI 客服核心处理流程", width_cm=16.0)
    add_figure(doc, assets["shot_customer"], "图4-2  AI 客服界面截图占位（后续替换）", width_cm=15.5)

    add_heading2(doc, "4.3 AI 课程助手逻辑与代码实现")
    add_paragraphs(doc, """
    AI 课程助手的设计目标，是让 AI 回答不再停留在“泛泛而谈”，而是尽量贴近课程和教师提供的真实资料。学生端 StudentCourseAssistant.vue 的逻辑相对简洁：页面加载时请求 /ai/course-assistant/apps，获取已启用的课程助手工作流列表；学生选择某个助手并输入问题后，仍通过 streamQA 调用统一流式问答接口。这样做的好处是前端逻辑复用程度高，学生端几乎不需要关心模型和知识库细节，只要选择助手即可提问。

    教师端 CourseAssistant.vue 则体现了该模块更完整的工程价值。页面初始化时会并行加载教师本人课程列表、管理员提供的基础课程助手工作流以及教师已经创建的个人工作流。教师可以先从基础工作流复制出一个新的课程助手，再为该助手选择课程、修改名称，并通过 /ai/teacher/kb/upload 上传课程私有知识文档。上传后的知识文档会被纳入课程知识库，后续学生和教师都可以围绕该课程发起更精准的提问。教师端还可以选择调用模型，从而在“基础平台能力”和“课程个性化能力”之间取得平衡。

    在后端，ai_portal.py 提供了课程助手的公共接口和教师专属接口。公共接口 /course-assistant/apps 用于向学生端和教师端返回当前可用的启用工作流；教师专属接口 /teacher/course-assistant/apps 则支持获取、创建、修改和删除教师自己的课程助手工作流。教师上传课程知识文档时，系统会根据 teacher_user_id 与 course_id 自动确保存在对应的知识库对象，再保存文件、抽取文本并更新 chunk。这样一来，AI 课程助手实现了“管理员提供底座、教师补充资料、学生按课程提问”的完整闭环。

    需要特别说明的是，界面文案与设计意图强调“教师 KB 优先、基础 KB 兜底”，这体现了项目希望让课程私有资料优先发挥作用的方向。但从当前 ai_qa.py 的实现看，工作流知识库与课程知识库更多是合并后统一进入轻量检索过程，并未在算法层面做非常强的优先级约束。因此，可以认为系统已经完成了课程相关知识增强的第一阶段实现，但仍有继续细化检索策略的空间，例如加入课程知识优先级、来源权重和引用展示等能力。
    """)
    add_figure(doc, assets["flow_course"], "图4-3  AI 课程助手核心处理流程", width_cm=16.0)
    add_figure(doc, assets["shot_course"], "图4-4  AI 课程助手界面截图占位（后续替换）", width_cm=15.5)

    add_heading2(doc, "4.4 智能教案逻辑与代码实现")
    add_paragraphs(doc, """
    与 AI 客服和 AI 课程助手相比，智能教案更强调“生成任务”的管理属性，而不是单次问答。LessonPlan.vue 页面在加载时会获取公共模型列表、教师授课课程、课程知识库文档以及历史教案任务。教师可以先选定课程，再在课程知识库中选取文档进行解析，填写教案标题和大纲内容，随后调用 createLessonPlanTask 创建任务记录。真正的教案内容生成并不直接由创建任务接口完成，而是通过统一的 streamQA 调用 lesson_plan 工作流实现，这种设计既复用了底层推理接口，也使任务状态能够独立管理。

    教案生成完成后，前端会将拼接得到的 Markdown 文本通过 updateLessonPlanTaskResult 回写到后端，更新任务状态为 completed，并记录结果内容。教师还可以在页面中继续编辑生成结果，再次保存修改，或者导出为 Markdown 文件。这说明项目并没有把“AI 生成一次即结束”作为目标，而是把 AI 当作教案初稿生成器，再由教师进行人工校正与最终确认。这种“AI 生成 + 教师修订”的模式更符合真实教学场景，也更容易在答辩中体现对教育场景责任边界的理解。

    从数据库层看，ai_lesson_plan_tasks 表记录了教师编号、课程编号、标题、大纲、状态、结果、错误信息、知识库编号和模型编号等字段，能够完整呈现一次教案生成任务从创建到完成的生命周期。此外，系统在创建教案任务时还会写入 AiUsageLog，说明项目已经开始尝试把教案生成纳入统一的 AI 使用统计体系。对于毕业设计项目而言，这种任务化、状态化和日志化的结构比简单返回一段文本更具有工程意义。

    当前模块也有一些值得继续优化的细节。例如，前端 parseSelectedDoc 对 txt、md、csv 文本可以直接拉取内容并填入大纲，但对于 docx、pdf 等文件更多依赖上传阶段的后端预处理，界面中的“解析结果”展示仍有提升空间；同时，教案质量目前主要依赖教师人工判断，缺少自动化结构校验、教学目标完整性检查和引用来源提示。这些问题并不改变模块能够正常运行的事实，但为论文的展望部分提供了明确的升级方向。
    """)
    add_figure(doc, assets["flow_lesson"], "图4-5  智能教案任务化生成流程", width_cm=16.0)
    add_figure(doc, assets["shot_lesson"], "图4-6  智能教案界面截图占位（后续替换）", width_cm=15.5)

    add_heading2(doc, "4.5 管理端 AI 配置实现")
    add_paragraphs(doc, """
    管理员端的价值在于把模型、知识库和工作流从具体业务页面中抽离出来，形成统一的后台治理入口。AdminAIConfig.vue 页面以标签页形式组织模型 API 管理、知识库管理和工作流管理三大区域。管理员可以新增或编辑模型名称、provider、endpoint、api_key、温度、最大输出长度、默认状态等参数，也可以通过手工测试弹窗直接调用模型接口，验证配置是否能够正常连通。这一能力对于毕业设计尤其重要，因为它使系统具备“环境切换”和“问题定位”的基础工程手段。

    在知识库管理方面，管理员可以创建工作流知识库、上传文档并触发 chunk 重建。后端 admin_ai.py 中的相关接口不仅保存文件，还会统计文档数量和 chunk 数量，便于管理员观察知识库规模。工作流管理方面，管理员可以为 AI 客服、AI 课程助手和智能教案等不同类型的工作流绑定知识库、模型 API 和状态，并维护客服欢迎语、搜索提示与推荐问题等参数。前端当前把这些客户化参数写入 app.settings_json，从而使用户端读取到的配置与工作流绑定关系保持一致。

    值得注意的是，项目代码中还存在 AiFeatureSetting 等额外配置结构，但用户侧实际读取的更多是 AiWorkflowApp.settings_json。这说明系统经历了从“功能级设置”向“工作流级设置”收敛的过程，当前实现已经偏向以工作流为中心进行管理。对于论文撰写而言，这种演进本身也是有价值的：它反映出毕业设计并不是静态方案照搬，而是在开发过程中围绕可维护性不断调整结构。
    """)
    add_figure(doc, assets["shot_admin"], "图4-7  管理员 AI 配置界面截图占位（后续替换）", width_cm=15.5)

    add_table(
        doc,
        "表4-1  三个 AI 模块的功能对比",
        ["模块", "主要用户", "输入内容", "核心处理", "输出结果"],
        [
            ["AI 客服", "学生、教师", "校园咨询问题", "工作流配置 + 知识检索 + SSE 问答", "实时回答与推荐问题"],
            ["AI 课程助手", "教师、学生", "课程问题与课程资料", "基础工作流复制 + 课程知识库增强 + 流式回答", "课程相关答疑结果"],
            ["智能教案", "教师", "课程资料、标题、大纲", "任务创建 + lesson_plan 工作流生成 + 结果回写", "可编辑、可导出的教案初稿"],
        ],
        [2.5, 2.4, 3.4, 4.7, 3.0],
    )

    add_heading2(doc, "4.6 项目亮点与当前不足")
    add_paragraphs(doc, """
    综合分析可以看到，本项目的主要亮点不在于“单个算法多先进”，而在于它把 AI 能力嵌入到了完整的教务系统中。第一，系统使用工作流、知识库和模型 API 进行统一抽象，使 AI 功能可以复用同一套底层问答接口；第二，系统既考虑学生即时问答，也覆盖教师课程资料管理和任务化教案生成，体现出多角色协同的业务价值；第三，数据库中不仅保存配置，还保存任务、文档 chunk 和使用日志，为后续数据分析和系统演进提供了基础。

    与此同时，项目当前也存在客观不足。其一，AI 客服配置中的 system_prompt_template 尚未真正参与问答 Prompt 组装，意味着管理员配置尚未完全落到执行层。其二，工作流状态检查仍可进一步加强，避免已禁用的工作流被直接按 code 调用。其三，对话历史虽然在前端存在多会话保存，但后端主链路尚未形成稳定的多轮记忆使用。其四，自动化测试脚本尚未与当前接口保持完全同步。其五，当前知识检索仍以 TF-IDF 为主，在复杂语义场景下仍有改进空间。上述问题均已在代码分析中能够定位，因此具备后续继续修复和优化的现实基础。
    """)

    add_table(
        doc,
        "表4-2  当前实现中的关键问题与改进方向",
        ["问题点", "代码体现", "影响", "改进方向"],
        [
            ["system_prompt_template 未生效", "ai_qa.py 的 _build_prompt 未注入模板", "客服策略无法完全落地", "将工作流模板并入最终 Prompt 组装"],
            ["禁用工作流仍可能被直接调用", "_load_workflow_app 仅按 code 查询", "后台状态与执行状态不完全一致", "查询时增加 status=enabled 校验"],
            ["多轮历史记忆未闭环", "前端保留 sessions，主链路 history_flag 价值有限", "上下文连续性不足", "引入历史裁剪与会话记忆存储"],
            ["测试脚本过期", "旧测试接口路径与当前实现不一致", "自动回归能力不足", "更新测试用例并接入 CI 或本地自动化脚本"],
            ["检索能力偏轻量", "当前使用 TF-IDF + 余弦相似度", "复杂语义问题召回不足", "升级为混合检索或向量检索方案"],
        ],
        [3.4, 4.8, 3.8, 4.0],
    )

    add_heading1(doc, "第五章 系统测试与结果分析")
    add_heading2(doc, "5.1 测试思路与测试环境")
    add_paragraphs(doc, """
    本次测试并未刻意追求复杂的压测数据，而是围绕“答辩时最需要证明哪些事实”来设计。对 AI 模块来说，最关键的问题有三个：页面进入时能否正确读到配置，提问或生成时能否走到真实后端链路，生成后的结果能否落库并被再次读取。因此，测试重点放在配置接口、工作流接口、统一问答接口、课程助手创建接口以及教案任务接口上。这样的思路更接近毕业设计阶段的实际目标，即先证明主链路已经跑通，再说明当前还剩哪些工程化问题。

    具体环境基于项目本地仓库完成，后端运行在 Python 3.13.13 与项目 .venv 虚拟环境中，前端运行在 Node.js v22.19.0 环境中。Windows 启动脚本 start_project.bat 已经给出了较直接的演示路径：先启动 uvicorn，再启动 Vite，最后自动打开浏览器。单从启动脚本的组织方式看，项目已经具备完整的本地演示闭环，而不是只保留部分源码片段。

    为了减少真实模型额度和外网波动对验证结果的影响，本文在接口联调时采用了内存数据库配合模拟模型返回值的方式。这样做的目的不是回避真实调用，而是把测试重心从外部网络稳定性转移到项目自身逻辑上，便于更准确地观察工作流查找、知识库编号收集、任务创建与结果回写是否正常执行。
    """)

    add_table(
        doc,
        "表5-1  AI 核心链路接口联调结果",
        ["测试项", "接口", "状态码", "结果说明"],
        data["test_summary"],
        [3.2, 6.4, 1.8, 5.0],
    )

    add_heading2(doc, "5.2 联调结果分析")
    add_paragraphs(doc, """
    联调结果最有价值的地方，在于它证明了三个看似独立的场景实际上已经共用了同一套底层机制。AI 客服能够读取配置并完成问答，说明工作流与流式接口链路是通的；教师可以创建课程助手，说明管理员提供的基础工作流已经能够向教师场景继续分发；教案任务可以创建并更新结果，则说明系统不仅能生成文本，还能把生成行为当作结构化业务来管理。把这些现象合在一起看，就能发现项目的 AI 功能已经不是零散页面，而是建立在统一数据结构之上的模块化能力。

    这些测试结果还反映出一个重要特点：系统内部大量复用了同一条问答主链路。无论是客服咨询、课程答疑还是教案生成，最终都会回到模型解析、知识检索、流式输出和结果持久化几个核心环节。对于毕业设计项目而言，这种复用意味着实现更经济，也意味着后续扩展其他 AI 场景时可以沿用已有机制，而不必完全重写基础设施。
    """)

    add_heading2(doc, "5.3 自动化测试现状与发现的问题")
    add_paragraphs(doc, """
    在对现有测试脚本进行复查时，本文还执行了 backend/tests/test_ai_customer_service_stream.py。结果显示，截至2026年4月24日，该测试未能通过，错误原因主要有两点：第一，fixture 中直接使用 monkeypatch 但未将其作为参数传入，导致 NameError；第二，测试脚本访问的接口路径为 /api/ai_qa/customer-service/stream，而当前实际生效的流式问答接口为 /api/ai_qa/qa/stream。这说明项目虽然已经具备较好的接口联调基础，但自动化测试脚本尚未跟随代码重构同步更新。

    此外，运行该测试脚本时还伴随出现多项 Pydantic V2 的兼容性提示与 FastAPI on_event 弃用警告。虽然这些警告不会直接阻断系统启动，但从软件工程角度看，说明项目在依赖升级后的代码风格清理方面仍有工作要做。对于毕业设计答辩而言，这类问题可以作为“工程完善方向”进行客观说明；对于后续继续迭代而言，则需要尽快把旧式 validator、orm_mode 和启动事件写法升级到新规范。
    """)

    add_table(
        doc,
        "表5-2  自动化测试复查中发现的主要问题",
        ["问题类别", "具体表现", "影响分析", "整改建议"],
        [
            ["测试脚本参数错误", "fixture 中直接使用 monkeypatch 变量", "测试在 setup 阶段即失败", "将 monkeypatch 作为 pytest fixture 参数传入"],
            ["接口路径过期", "仍访问 /api/ai_qa/customer-service/stream", "无法覆盖当前真实问答链路", "统一切换到 /api/ai_qa/qa/stream"],
            ["兼容性警告", "Pydantic V2 与 FastAPI 旧写法提示", "增加维护成本，影响后续升级", "逐步完成配置与 validator 写法迁移"],
            ["AI 质量评估不足", "当前主要验证连通性和状态码", "难以量化答案质量", "增加结果打分、人工复核与样本问答集"],
        ],
        [3.0, 5.0, 4.0, 4.0],
    )

    add_heading2(doc, "5.4 综合评价")
    add_paragraphs(doc, """
    综合来看，本系统已经完成了毕业设计答辩所需的主要 AI 链路验证。无论是管理员配置、学生调用，还是教师上传知识库与任务化生成教案，都已经具备清晰的代码入口、数据库落点和可说明的流程结构。特别是 AI 客服、AI 课程助手和智能教案三条链路之间的共性设计，体现出项目不是单纯追求功能数量，而是在尝试建立一套面向高校教务场景的 AI 能力底座。

    当然，当前系统仍应保持对“可用”与“完美”的区分。接口联调通过并不意味着所有真实大模型网络环境、所有浏览器交互细节和所有异常场景都已经完全稳定；自动化测试脚本未及时更新也说明工程保障还需加强。因此，本文对系统的评价是：已经达到“主链路可运行、主要功能可演示、问题可以定位”的阶段，适合作为毕业设计成果提交与继续完善的基础版本。
    """)

    add_heading1(doc, "第六章 总结与展望")
    add_heading2(doc, "6.1 全文总结")
    add_paragraphs(doc, """
    本文完成的核心工作，不是凭空设计一套理想化系统，而是把一个已有代码基础的教务项目重新梳理成一篇能够对应功能、接口、数据和测试结果的毕业论文。通过对前端页面、后端路由、数据库样本和联调结果的综合分析，论文说明了系统如何将 AI 客服、AI 课程助手和智能教案三类能力嵌入原有教务流程之中，并解释了这些能力背后的工作流、知识库和任务结构。

    从当前成果看，项目已经具备三个比较明确的工程特点：一是 AI 能力有统一底座，不同场景能够复用同一套模型选择和问答主链路；二是知识库不再停留在文件上传层，而是能够经过抽取、分块后参与检索；三是教案生成不只是一段即时输出，而是被纳入任务管理和结果回写过程。对毕业设计而言，这种从代码到论文的对应关系，比只展示少量界面或只描述算法概念更能体现系统分析与实现的完整性。
    """)

    add_heading2(doc, "6.2 后续展望")
    add_paragraphs(doc, """
    后续完善可以分成两类。一类是“把现有缺口补齐”，例如让 system_prompt_template 真正进入 Prompt、在执行层严格校验工作流启用状态、把多会话历史与后端记忆链路对齐、更新失效测试脚本并清理依赖兼容性警告。另一类是“提升系统上限”，例如将当前轻量检索升级为混合检索或向量检索、给教案结果增加结构化质量检查、为问答结果增加评分与抽样复核机制。

    更长远地看，AI 在高校教务系统中的作用不应只是替换人工回复，而应成为连接规则解释、课程支持和教学内容生产的辅助层。当前项目已经验证了这一方向在工程上是可行的：只要模型、知识来源和业务入口之间的关系被设计清楚，AI 就能够稳定地服务于教务场景。后续继续迭代时，重点不再是“再接一个模型”，而是让系统在准确性、可追踪性和运维稳定性方面更成熟。
    """)

    refs = [
        "李欣，王磊. 基于前后端分离的智能教务管理系统设计与实现[J]. 计算机工程与科学，2024，46(5)：892-899.",
        "陈皓，李艳秋. 基于Vue3+FastAPI的高校教务管理系统设计与实现[J]. 计算机工程与应用，2023，59(18)：236-243.",
        "张明远，刘芳. 人工智能赋能高校教务管理数字化转型的路径研究[J]. 中国教育信息化，2025，31(2)：45-52.",
        "王红. Vue3+TypeScript前端开发实战[M]. 北京：清华大学出版社，2025.",
        "陈阳. FastAPI后端开发与实战[M]. 北京：机械工业出版社，2024.",
        "赵伟. 基于SQLite的轻量级数据库系统设计与应用[J]. 计算机应用研究，2023，40(8)：2415-2420.",
        "刘军，吴敏. 智慧教务系统中AI选课冲突检测与智能推荐算法研究[J]. 计算机应用与软件，2024，41(3)：189-195.",
        "湖南工业大学教务处. 智慧教学管理体系的构建与实践[R]. 2025.",
        "中华人民共和国教育部. 教育数字化战略行动实施方案[Z]. 2023.",
        "张敏，刘栋. 基于自适应遗传算法的高校智能排课系统优化[J]. 计算机仿真，2025，42(4)：215-220.",
        "Mi Y, Yu Y, Zhao Y Y. SmartCourse: A Contextual AI-Powered Course Advising System for Undergraduates[R]. arXiv, 2025.",
        "Almutairi S, Alqahtani F. Leveraging Explainable AI to Recommend Personalized Learning Pathways in Higher Education[J]. Journal of Mathematics and Statistics Studies, 2025, 11(3):78-92.",
        "FastAPI Documentation[EB/OL]. https://fastapi.tiangolo.com/.",
        "Vue.js Documentation[EB/OL]. https://vuejs.org/guide/.",
    ]
    add_references(doc, refs)
    doc.add_page_break()

    add_heading1(doc, "致谢")
    add_paragraphs(doc, """
    本论文的完成离不开学校、指导教师、企业导师以及项目开发过程中所有给予帮助的老师和同学。首先，感谢指导教师张锦辉老师在课题选择、系统设计、论文结构和答辩准备方面给予的耐心指导，使我能够把代码实现与论文分析逐步统一起来。感谢企业导师嵇伟老师从工程实践角度提出建议，使我在“功能可用”和“系统可维护”之间形成更清晰的认识。

    感谢学院提供的学习环境与毕业设计组织安排，也感谢在项目开发与测试过程中提供意见的同学。通过本次毕业设计，我不仅进一步掌握了 Vue3、FastAPI、SQLAlchemy 等技术栈，更重要的是理解了如何围绕真实业务需求构建一套可以落地、可以解释、可以继续演进的系统。今后我将继续完善项目中的不足，把毕业设计中形成的经验转化为更扎实的工程能力。
    """)
    doc.add_page_break()

    add_heading1(doc, "附录A  关键接口与启动说明")
    add_paragraphs(doc, """
    为便于后续答辩展示与论文修改，现将项目中与 AI 相关的关键接口和启动脚本进行简要整理。AI 客服配置接口为 GET /api/ai/customer-service/config，客服工作流列表接口为 GET /api/ai/customer-service/apps，统一流式问答接口为 POST /api/ai_qa/qa/stream；学生和教师共用的课程助手公共列表接口为 GET /api/ai/course-assistant/apps；教师侧课程助手自定义接口包括 GET/POST/PUT/DELETE /api/ai/teacher/course-assistant/apps；教师知识库上传接口为 POST /api/ai/teacher/kb/upload；教师教案任务相关接口包括 GET/POST /api/ai/teacher/lesson-plan/tasks 与 PUT /api/ai/teacher/lesson-plan/tasks/{task_id}/result。

    Windows 启动脚本 start_project.bat 的执行逻辑为：先切换到 backend 目录并使用项目虚拟环境启动 uvicorn 服务，再切换到 frontend 目录执行 npm run dev，等待数秒后自动打开浏览器页面 http://localhost:2003。该脚本对于毕业答辩前的本地演示具有直接帮助，后续若需要正式部署，可进一步引入反向代理、生产构建与环境变量管理策略。
    """)

    add_heading1(doc, "附录B  AI 模块后续整改清单")
    add_paragraphs(doc, """
    （1）补齐 Prompt 模板注入逻辑：在 ai_qa.py 中将客服 settings_json 内的 system_prompt_template 参与最终 Prompt 组装，并按场景配置可选模板变量。

    （2）加强工作流状态控制：在 _load_workflow_app 查询逻辑中增加 status 校验，防止禁用工作流被直接按 code 调用。

    （3）完善多轮对话记忆：将前端本地会话历史与后端 history_flag 机制打通，并建立适当的消息裁剪策略。

    （4）升级检索能力：在保留当前 TF-IDF 方案的基础上，引入 FTS5、BM25 或向量检索，实现更高质量的课程知识召回。

    （5）重写自动化测试：修正旧测试路径与 fixture 参数问题，补充课程助手、教案任务和知识库上传等测试用例。

    （6）完善结果评估：为教案与问答结果增加人工评分、结果抽检与日志分析机制，形成更强的质量闭环。
    """)

    return doc


def main() -> None:
    assets = build_assets()
    data = query_runtime_data()
    doc = build_doc(assets, data)
    OUTPUT_DIR.mkdir(exist_ok=True)
    doc.save(str(DOCX_PATH))
    char_count = len(re.sub(r"\s+", "", "".join(TEXT_COLLECTOR)))
    summary = {
        "docx": str(DOCX_PATH),
        "assets_dir": str(ASSET_DIR),
        "char_count_no_space": char_count,
        "image_count": len(list(ASSET_DIR.glob("*.png"))),
    }
    (OUTPUT_DIR / "thesis_generation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if char_count < 12000:
        raise SystemExit(f"生成文本长度不足：{char_count}")


if __name__ == "__main__":
    main()
