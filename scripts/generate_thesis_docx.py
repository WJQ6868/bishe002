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
DOCX_PATH = ROOT / "AI赋能的高校教务系统-毕业论文润色定稿版.docx"
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


def draw_poly_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    label: str | None = None,
    color=(52, 73, 94),
    width: int = 4,
) -> None:
    if len(points) < 2:
        return
    draw.line(points, fill=color, width=width)
    start = points[-2]
    end = points[-1]
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    arrow_len = 16
    angle1 = angle - math.pi / 8
    angle2 = angle + math.pi / 8
    p1 = (end[0] - arrow_len * math.cos(angle1), end[1] - arrow_len * math.sin(angle1))
    p2 = (end[0] - arrow_len * math.cos(angle2), end[1] - arrow_len * math.sin(angle2))
    draw.polygon([end, p1, p2], fill=color)
    if label:
        font = load_font(20, bold=True)
        first = points[0]
        last = points[-1]
        mx = (first[0] + last[0]) // 2
        my = (first[1] + last[1]) // 2 - 18
        draw_centered_text(draw, (mx, my), label, font, fill=(44, 62, 80))


def draw_round_box_custom(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    lines: list[str] | None = None,
    *,
    title_size: int = 28,
    body_size: int = 20,
    title_top: int = 14,
    line_gap: int = 28,
    fill=(248, 250, 252),
    outline=(52, 73, 94),
    title_fill=(52, 73, 94),
    radius: int = 18,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=3)
    title_font = load_font(title_size, bold=True)
    body_font = load_font(body_size)
    draw.text((x1 + 18, y1 + title_top), title, font=title_font, fill=title_fill)
    if lines:
        y = y1 + title_top + title_size + 16
        for line in lines:
            wrapped = wrap_text(draw, line, body_font, x2 - x1 - 36)
            for item in wrapped:
                draw.text((x1 + 18, y), item, font=body_font, fill=(33, 37, 41))
                y += line_gap


def draw_entity_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    fields: list[str],
    *,
    fill=(248, 250, 252),
    outline=(52, 73, 94),
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=18, fill=fill, outline=outline, width=3)
    title_font = load_font(24, bold=True)
    body_font = load_font(18)
    draw.text((x1 + 16, y1 + 12), title, font=title_font, fill=(44, 62, 80))
    divider_y = y1 + 50
    draw.line((x1 + 10, divider_y, x2 - 10, divider_y), fill=outline, width=2)
    y = divider_y + 12
    for field in fields:
        wrapped = wrap_text(draw, field, body_font, x2 - x1 - 32)
        for item in wrapped:
            draw.text((x1 + 16, y), item, font=body_font, fill=(33, 37, 41))
            y += 24


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
    img = Image.new("RGB", (4200, 2500), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw_centered_text(draw, (2100, 86), "高校教务系统总体架构图", load_font(76, bold=True))

    top_boxes = [
        ((180, 220, 1120, 560), "学生端", ["课程查询、请假申请、AI 客服、AI 课程助手、查看共享教案"], (234, 244, 252)),
        ((1630, 220, 2570, 560), "教师端", ["课程管理、作业批改、课程助手、知识库上传、智能教案生成"], (237, 249, 241)),
        ((3080, 220, 4020, 560), "管理员端", ["用户管理、数据维护、模型配置、知识库管理、工作流编排"], (252, 244, 234)),
    ]
    for box, title, lines, fill in top_boxes:
        draw_round_box_custom(draw, box, title, lines, title_size=68, body_size=50, line_gap=62, fill=fill, radius=28)

    front_box = (260, 760, 3940, 1140)
    back_box = (220, 1380, 3980, 1900)
    draw_round_box_custom(
        draw,
        front_box,
        "前端展示层（Vue3 + TypeScript + Element Plus + Pinia + Vue Router）",
        ["统一路由、角色化界面、Axios 请求封装、SSE 流式结果渲染、即时消息与可视化组件"],
        title_size=66,
        body_size=48,
        line_gap=60,
        fill=(246, 248, 252),
        radius=28,
    )
    draw_round_box_custom(
        draw,
        back_box,
        "后端服务层（FastAPI + SQLAlchemy + Socket.IO）",
        [
            "认证授权、课程管理、办事大厅、成绩与请假、管理员 AI 配置、AI Portal、AI QA 路由",
            "统一通过依赖注入获取用户与数据库会话，支持 /api 前缀接口与静态文件访问",
        ],
        title_size=66,
        body_size=48,
        line_gap=60,
        fill=(245, 245, 255),
        radius=28,
    )

    lower_boxes = [
        ((160, 2120, 1140, 2470), "AI 配置编排层", ["模型 API 管理、工作流绑定、客服参数维护、模型测试与启停控制"], (244, 249, 255)),
        ((1160, 2120, 2140, 2470), "知识组织层", ["基础知识库、课程私有知识库、文档抽取、文本切分、Chunk 元数据存储"], (244, 255, 249)),
        ((2160, 2120, 3140, 2470), "推理执行层", ["TF-IDF 检索、Prompt 组装、模型选择、SSE 流式输出、结果持久化"], (255, 250, 244)),
        ((3160, 2120, 4040, 2470), "数据与外部资源层", ["SQLite 数据库", "静态上传文件", "DashScope / Ark 模型接口"], (250, 244, 255)),
    ]
    for box, title, lines, fill in lower_boxes:
        draw_round_box_custom(draw, box, title, lines, title_size=60, body_size=46, line_gap=58, fill=fill, radius=28)

    for cx in (650, 2100, 3550):
        draw_poly_arrow(draw, [(cx, 560), (cx, 650), (2100, 650), (2100, 760)], width=7)
    draw_poly_arrow(draw, [(2100, 1140), (2100, 1380)], width=7)
    for cx in (650, 1650, 2650, 3600):
        draw_poly_arrow(draw, [(2100, 1900), (2100, 2005), (cx, 2005), (cx, 2120)], width=7)

    note_font = load_font(46)
    draw.text(
        (180, 2425),
        "说明：系统采用前后端分离架构，AI 能力以工作流形式嵌入学生端、教师端和管理员端业务场景。",
        font=note_font,
        fill=(60, 60, 60),
    )
    img.save(path)


def create_ai_closed_loop(path: Path) -> None:
    img = Image.new("RGB", (4000, 2400), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw_centered_text(draw, (2000, 86), "AI 业务闭环与分层实现逻辑", load_font(76, bold=True))

    stage_boxes = [
        ((140, 220, 920, 560), "配置端", ["管理员配置模型、知识库、工作流与客服参数"], (234, 244, 252)),
        ((1080, 220, 1860, 560), "业务端", ["学生/教师按角色调用 AI 客服、AI 课程助手、智能教案"], (237, 249, 241)),
        ((2020, 220, 2800, 560), "数据回流", ["生成任务、日志、问答记录、课程资料更新"], (252, 244, 234)),
        ((2960, 220, 3740, 560), "优化闭环", ["补充知识库、调整模型、修正提示词与工作流策略"], (250, 244, 255)),
    ]
    for box, title, lines, fill in stage_boxes:
        draw_round_box_custom(draw, box, title, lines, title_size=64, body_size=46, line_gap=58, fill=fill, radius=28)
    draw_poly_arrow(draw, [(920, 390), (1080, 390)], width=7)
    draw_poly_arrow(draw, [(1860, 390), (2020, 390)], width=7)
    draw_poly_arrow(draw, [(2800, 390), (2960, 390)], width=7)
    draw_poly_arrow(draw, [(3350, 560), (3350, 700), (520, 700), (520, 600)], label="反馈", width=7)

    outer = (220, 940, 3780, 2240)
    draw.rounded_rectangle(outer, radius=30, fill=(248, 248, 250), outline=(52, 73, 94), width=5)
    draw.text((300, 995), "四层 AI 架构", font=load_font(72, bold=True), fill=(44, 62, 80))
    row_boxes = [
        ((380, 1180, 3620, 1380), "第一层：AI 配置编排层", ["模型 API、知识库、工作流 App 与功能参数统一由后台管理"], (244, 249, 255)),
        ((380, 1480, 3620, 1680), "第二层：知识组织层", ["教师上传资料，系统抽取文本并切分片段，为问答和教案生成提供上下文"], (244, 255, 249)),
        ((380, 1780, 3620, 1980), "第三层：推理执行层", ["根据请求解析工作流、选择模型、检索知识片段、拼装 Prompt 并调用模型"], (255, 250, 244)),
        ((380, 2080, 3620, 2280), "第四层：业务接入层", ["AI 客服、AI 课程助手、智能教案三类场景分别面向师生与管理端落地"], (250, 244, 255)),
    ]
    for box, title, lines, fill in row_boxes:
        draw_round_box_custom(draw, box, title, lines, title_size=60, body_size=46, line_gap=58, fill=fill, radius=26)
    img.save(path)


def create_ai_er(path: Path) -> None:
    img = Image.new("RGB", (4800, 2800), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    line_color = (52, 73, 94)
    text_color = (33, 37, 41)

    def entity_box(box: tuple[int, int, int, int], title: str, fields: list[str], *, fill) -> None:
        x1, y1, x2, y2 = box
        draw.rounded_rectangle(box, radius=28, fill=fill, outline=line_color, width=5)
        title_font = load_font(58, bold=True)
        body_font = load_font(46)
        draw.text((x1 + 24, y1 + 18), title, font=title_font, fill=line_color)
        divider_y = y1 + 102
        draw.line((x1 + 18, divider_y, x2 - 18, divider_y), fill=line_color, width=3)
        y = divider_y + 18
        for field in fields:
            for item in wrap_text(draw, field, body_font, x2 - x1 - 48):
                draw.text((x1 + 24, y), item, font=body_font, fill=text_color)
                y += 58

    def big_arrow(points: list[tuple[int, int]], label: str | None = None, label_xy: tuple[int, int] | None = None) -> None:
        if len(points) < 2:
            return
        draw.line(points, fill=line_color, width=7)
        start = points[-2]
        end = points[-1]
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        arrow_len = 26
        angle1 = angle - math.pi / 8
        angle2 = angle + math.pi / 8
        p1 = (end[0] - arrow_len * math.cos(angle1), end[1] - arrow_len * math.sin(angle1))
        p2 = (end[0] - arrow_len * math.cos(angle2), end[1] - arrow_len * math.sin(angle2))
        draw.polygon([end, p1, p2], fill=line_color)
        if label:
            label_font = load_font(42, bold=True)
            lx, ly = label_xy or ((points[0][0] + points[-1][0]) // 2, (points[0][1] + points[-1][1]) // 2 - 26)
            padding_x, padding_y = 18, 10
            bbox = draw.textbbox((0, 0), label, font=label_font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            draw.rounded_rectangle((lx - w / 2 - padding_x, ly - h / 2 - padding_y, lx + w / 2 + padding_x, ly + h / 2 + padding_y), radius=16, fill=(255, 255, 255))
            draw_centered_text(draw, (lx, ly), label, label_font, fill=line_color)

    draw_centered_text(draw, (2400, 78), "AI 核心数据 ER 图", load_font(88, bold=True))

    boxes = {
        "sys_users": (120, 220, 1040, 760),
        "courses": (120, 1470, 1040, 2110),
        "ai_model_apis": (1230, 220, 2260, 960),
        "ai_knowledge_bases": (1230, 1240, 2260, 2080),
        "ai_workflow_apps": (2450, 220, 3570, 1020),
        "ai_kb_documents": (2450, 1470, 3570, 2240),
        "ai_lesson_plan_tasks": (3740, 220, 4680, 1020),
        "ai_kb_chunks": (3740, 1470, 4680, 2310),
    }
    entity_box(boxes["sys_users"], "sys_users", ["PK id", "username", "role", "is_active"], fill=(234, 244, 252))
    entity_box(boxes["courses"], "courses", ["PK id", "name", "teacher_id", "credit", "capacity", "course_type"], fill=(237, 249, 241))
    entity_box(boxes["ai_model_apis"], "ai_model_apis", ["PK id", "name", "provider", "model_name", "endpoint", "enabled", "is_default"], fill=(252, 244, 234))
    entity_box(boxes["ai_knowledge_bases"], "ai_knowledge_bases", ["PK id", "slug", "name", "owner_type", "owner_user_id", "course_id", "feature"], fill=(250, 244, 255))
    entity_box(boxes["ai_workflow_apps"], "ai_workflow_apps", ["PK id", "code", "type", "name", "knowledge_base_id", "model_api_id", "owner_user_id", "course_id", "status"], fill=(246, 248, 252))
    entity_box(boxes["ai_kb_documents"], "ai_kb_documents", ["PK id", "knowledge_base_id", "title", "original_filename", "url", "file_ext", "enabled"], fill=(244, 249, 255))
    entity_box(boxes["ai_lesson_plan_tasks"], "ai_lesson_plan_tasks", ["PK id", "teacher_user_id", "course_id", "title", "status", "result", "knowledge_base_id", "model_api_id"], fill=(255, 250, 244))
    entity_box(boxes["ai_kb_chunks"], "ai_kb_chunks", ["PK id", "knowledge_base_id", "document_id", "seq", "content", "tokens", "document_title"], fill=(244, 255, 249))

    big_arrow([(1040, 410), (1230, 410)], "用户拥有/配置", (1130, 360))
    big_arrow([(1040, 1730), (1230, 1730)], "课程关联", (1130, 1675))
    big_arrow([(2260, 460), (2450, 460)], "模型绑定", (2350, 405))
    big_arrow([(2260, 1430), (2360, 1430), (2360, 760), (2450, 760)], "工作流知识库", (2350, 1090))
    big_arrow([(2260, 1730), (2450, 1730)], "1:N", (2350, 1675))
    big_arrow([(3570, 1810), (3740, 1810)], "1:N", (3655, 1760))
    big_arrow([(3570, 460), (3740, 460)], "任务模型", (3655, 405))
    big_arrow([(3570, 760), (3740, 760)], "任务知识库", (3655, 705))
    big_arrow([(4210, 1470), (4210, 1045)], "教案引用知识分块", (4410, 1260))

    note_font = load_font(42)
    note = "说明：该 ER 图重点表现模型、知识库、工作流、文档分块与教案任务之间的主关联关系，并与用户、课程主表相连接。"
    draw.text((120, 2660), note, font=note_font, fill=(60, 60, 60))
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
    本文以 AI 赋能的高校教务系统毕业设计项目为研究对象，依托实际代码仓库、数据库样本、启动脚本与本地联调结果，对系统的功能构成、AI 模块实现路径及运行现状进行了系统分析。与仅依据需求文档开展论述的研究方式相比，本文更加注重从既有实现出发，对系统已经落地的功能链路、当前可验证的运行状态以及仍需完善的工程环节进行客观归纳。

    该系统采用前后端分离架构。前端基于 Vue3、TypeScript、Element Plus、Pinia 与 Vue Router 构建学生端、教师端和管理员端页面；后端基于 FastAPI、SQLAlchemy 与 SQLite 提供统一接口、数据持久化和业务支撑，并结合 Socket.IO 实现即时通信能力。在传统教务业务模块基础上，系统进一步引入模型管理、知识库管理、工作流绑定、流式问答以及教案任务回写等 AI 相关功能，从而形成面向教务场景的智能化扩展框架。

    论文重点围绕三个核心 AI 应用场景展开分析。其一，AI 客服通过工作流配置读取、知识片段检索和 SSE 流式输出，为学生和教师提供统一的教务咨询服务入口。其二，AI 课程助手支持教师在基础工作流之上构建个人课程助手，并将课程资料转化为私有知识库，以增强课程问答的针对性。其三，智能教案模块采用任务化处理模式，将教案生成、结果回写、二次编辑与导出操作纳入统一流程管理。底层检索机制采用 TF-IDF 与余弦相似度进行文本召回，形成了适用于本课题场景的轻量级检索增强生成方案。

    截至2026年4月24日，项目本地数据库中已保存 4 条模型 API 配置、4 个知识库、3 份知识库文档、86 个知识片段、4 个工作流应用以及 3 条教案任务记录。基于内存数据库和模拟模型响应开展的接口联调结果显示，客服配置读取、工作流列表获取、统一问答接口调用、教师创建课程助手、创建教案任务及结果回写等关键接口均能够返回 HTTP 200，表明系统已具备毕业设计答辩所需的主链路运行基础。

    在总结系统实现成效的同时，本文亦对现阶段存在的不足进行了说明，包括 system_prompt_template 尚未注入最终 Prompt、禁用工作流缺少执行层严格校验、多轮对话记忆链路尚未完整闭合，以及部分旧测试脚本未与当前接口保持同步等问题。上述分析表明，本研究的价值不仅在于展示系统已实现的功能，更在于基于真实代码状态提出可验证、可延续的优化方向。
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
    当前高校教务管理正由传统信息化阶段向智能化服务阶段逐步演进。一方面，课程管理、请假审批、成绩查询、办事大厅等业务已基本实现线上化与流程化；另一方面，大模型在自然语言理解、文本生成和知识问答方面的能力持续提升，为教务系统引入智能咨询、课程支持和教学内容辅助生成提供了新的技术条件。然而，从现有系统建设情况看，许多教务平台仍以事务处理为主，尚未形成与具体业务流程深度耦合的 AI 服务体系。

    从实际应用需求出发，学生在办理业务时往往面临流程认知不足、规则理解不充分和页面入口分散等问题；教师在课程资源整理、重复性答疑和教案编制过程中仍需投入较多时间；管理员虽然掌握系统配置权限，但在模型接入、知识源管理和场景化能力编排方面缺少统一治理工具。因此，教务系统的升级不宜停留于页面增设或模块叠加，而应当将可解释、可配置、可追踪的 AI 服务嵌入既有业务流程之中 [3][9]。

    本课题的研究意义主要体现在工程实现与场景验证两个层面。理论层面，本文尝试论证高校教务 AI 不应被理解为单一通用对话功能，而应由模型配置、知识组织、工作流调度与业务接入共同构成。实践层面，系统围绕 AI 客服、AI 课程助手和智能教案三个典型场景展开实现，并结合数据库实体、接口联调结果与代码复查情况，对系统的可运行性、可说明性和可扩展性进行综合分析，从而为高校教务系统的智能化建设提供具有现实依据的案例支撑。
    """)

    add_heading2(doc, "1.2 国内外研究现状")
    add_paragraphs(doc, """
    国内高校教务系统研究长期围绕课程管理、成绩管理、排课管理、权限控制与办事流程展开，相关成果多聚焦于前后端分离架构、数据库规范化设计、流程在线化与数据可视化等方向 [1][2]。随着人工智能技术在教育领域的持续渗透，部分研究开始关注智能排课、学情分析、学习推荐与在线问答等应用 [7][10]。然而，从现有实现看，不少系统仍停留在单点式能力接入阶段，例如仅嵌入通用聊天窗口，或将大模型简单用作信息检索替代工具，尚未有效解决知识来源可信性、业务权限控制和结果反馈闭环等关键问题。

    国外在课程推荐、学业规划、个性化学习路径与可解释教育 AI 等方面起步较早，部分研究强调依据课程语境、学生行为与学习目标提供更具针对性的支持 [11][12]。此类研究表明，教育场景下 AI 系统的有效性并不完全取决于模型的通用能力，而更依赖其与具体课程、具体角色和具体数据约束之间的匹配程度。然而，国外相关系统大多构建于学习平台或教学支持平台之上，在管理流程、审批制度和角色组织方面与我国高校教务体系存在明显差异，因而难以直接迁移到本地教务管理场景。

    综合国内外研究成果可以看出，当前研究的关键不足并非 AI 功能的缺位，而是 AI 与教务业务结构融合深度不足。其主要表现为：模型能力缺少统一后台编排，知识库组织与课程和角色脱节，模型输出结果缺乏日志、任务或状态记录，难以支撑后续复盘与持续优化。基于上述问题，本文将研究重点放在 AI 配置能力、知识组织能力和业务接入能力的一体化实现上，以弥补现有研究中“场景存在而工程闭环不足”的实践缺口。
    """)

    add_heading2(doc, "1.3 研究目标、内容与技术路线")
    add_paragraphs(doc, """
    本课题的研究目标，是在既有多角色教务系统基础上构建并分析一套具有 AI 服务能力的可演示系统，并对其核心实现逻辑进行系统化阐释。围绕这一目标，本文从三个层面展开研究：其一，梳理学生、教师和管理员在系统中的业务入口与使用边界；其二，分析模型、知识库、工作流与任务表之间的协同关系；其三，结合本地联调与测试复查结果，对系统主链路的可运行性进行验证。

    对应研究内容，本文主要完成以下四项工作：第一，分析系统的角色需求、业务边界及 AI 模块定位，明确 AI 在教务系统中承担的是增强与辅助功能，而非替代既有业务流程；第二，梳理 ai_model_apis、ai_knowledge_bases、ai_workflow_apps、ai_lesson_plan_tasks 等核心数据结构，说明其在系统中的组织方式；第三，围绕 AI 客服、AI 课程助手和智能教案三个模块，解析前后端实现逻辑及其业务流程；第四，结合接口联调、数据库样本与测试脚本复查结果，对系统当前的可用性与不足进行综合评价。

    本文采用“先核实实现、再归纳结构”的技术路线。具体而言，首先对前端页面、接口封装和角色入口进行梳理，以明确用户交互路径；其次分析后端路由、服务函数和数据模型，厘清工作流解析、知识检索和模型调用的处理顺序；再次结合数据库现有数据和本地验证结果，确认关键链路是否贯通；最后依据发现的问题提出后续优化方向。该技术路线有助于确保论文叙述与项目当前代码状态保持一致，增强研究结论的真实性与可验证性。
    """)

    add_heading2(doc, "1.4 论文结构安排")
    add_paragraphs(doc, """
    全文共分为六章。第一章阐述课题背景、研究意义、国内外研究现状以及本文的研究目标与技术路线。第二章从业务场景出发，对系统的角色需求、功能需求、非功能需求及总体架构进行分析。第三章围绕前后端技术栈、知识库组织机制、轻量级检索增强生成方案与数据库设计展开论述。第四章重点分析 AI 客服、AI 课程助手、智能教案及管理端 AI 配置模块的实现逻辑。第五章给出系统测试思路、接口联调结果与问题复查结论。第六章对全文进行总结，并对后续优化方向作出展望。文末附参考文献、致谢与附录内容，以支撑论文的完整呈现。
    """)

    add_heading1(doc, "第二章 需求分析与总体设计")
    add_heading2(doc, "2.1 业务场景与角色需求分析")
    add_paragraphs(doc, """
    本文的需求分析以项目现有页面、接口和数据结构为基础展开，而非停留于抽象角色描述。对于学生用户而言，系统已提供课程查询、请假申请、办事大厅与证书查看等基础功能，因此其对 AI 的核心诉求并不在于新增独立入口，而在于借助自然语言交互快速理解业务流程、明确办理条件并获取课程相关学习支持。

    教师用户的需求重点则体现为课程资源组织与教学辅助。结合教师端页面设计可以看出，AI 课程助手与智能教案模块均围绕课程资料展开，因此教师更加关注知识文档上传便捷性、课程绑定准确性、生成内容的可编辑性以及结果沉淀能力。换言之，教师需要的是面向具体课程场景的辅助工具，而非缺乏边界约束的通用聊天能力。

    管理员用户的需求主要集中于配置治理与运行控制。管理员并非系统中的高频提问者，但需要对模型可用性、知识库归属关系、工作流开放范围以及界面参数配置进行统一管理。因此，在本系统中，管理员承担 AI 资源编排与治理职能。正是由于学生、教师与管理员在使用目标和操作权限方面存在显著差异，系统在设计上必须同时引入角色分层与工作流分层机制。
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
    从代码结构与业务定位来看，系统功能可以划分为基础教务业务层与 AI 增强业务层。前者负责承载课程、请假、办事流程和用户管理等校园真实业务；后者在此基础上补充问答服务、课程资料辅助和教学内容生成能力。该划分方式能够保证 AI 功能直接依托既有课程、用户和权限体系运行，避免脱离业务场景而形成孤立功能。

    具体而言，AI 客服模块的功能需求不仅包括问答能力本身，还涉及配置读取、工作流切换与流式输出等环节。因此，其完整功能链应包含：管理员维护客服工作流与展示参数、前端组件进入页面后自动加载配置、用户提交问题并调用统一流式接口、后端依据工作流绑定的知识库和模型返回结果。AI 课程助手的功能链则进一步延伸至教师侧个性化配置，要求系统支持基础工作流复制、课程资料上传以及资料参与检索问答。

    智能教案模块体现出更为明显的任务型特征。教师在使用过程中需要经历课程选择、资料选取、任务创建、内容生成、结果修改、保存和导出等多个步骤。因此，该模块的核心需求并非单纯追求生成速度，而是确保生成过程具备可记录性、生成结果具备可复用性、异常情况具备可定位性。基于这一需求，系统以 ai_lesson_plan_tasks 表对教案生成过程进行结构化管理，而非仅返回一次性文本结果。
    """)

    add_heading2(doc, "2.3 非功能需求分析")
    add_paragraphs(doc, """
    非功能需求决定了系统在实际部署与后续维护中的稳定性与可持续性。从当前实现情况看，系统的可维护性首先来源于相对清晰的结构分层：前端页面、接口封装、后端路由、数据模型与服务函数边界明确，AI 模块的引入并未破坏原有教务业务的组织结构。其次，可扩展性体现在模型、知识库和工作流被抽象为独立配置对象，后续如需更换模型供应商或扩展新的 AI 场景，无需整体重构现有页面和业务链路。

    在可用性方面，系统已体现出较为明确的界面与交互策略。一方面，通过角色分流机制控制不同用户可见入口，学生侧主要面向提问与使用，配置性操作则集中于教师和管理员端；另一方面，通过 SSE 流式输出机制改善问答类交互的等待体验。安全性方面，后端依托当前用户身份与角色校验限制敏感操作，例如教师上传课程资料前需完成课程归属验证，管理员相关接口仅向具备相应权限的用户开放。

    对于 AI 模块而言，结果可解释性与故障可处理性同样构成重要的非功能要求。当前系统通过知识分块、任务状态记录、工作流绑定关系与错误提示信息尽可能保留关键链路数据。虽然这些机制尚未构成完整的质量评估体系，但已显著优于仅返回模型文本结果的简单实现方式，为后续问题定位、性能优化和责任边界分析提供了必要基础。
    """)

    add_heading2(doc, "2.4 系统总体架构设计")
    add_paragraphs(doc, """
    结合项目代码实现可知，系统总体采用“前端展示层—后端服务层—AI 能力层—数据与外部资源层”的分层架构。前端以 Vue3 与 TypeScript 完成页面渲染和交互逻辑组织，Pinia 用于状态管理，Axios 负责常规 HTTP 请求，浏览器原生 fetch 配合自定义解析逻辑完成 SSE 流式问答。后端以 FastAPI 承载路由注册、依赖注入与接口组织，SQLAlchemy 负责 ORM 建模和数据库会话管理，Socket.IO 用于补充即时通信能力，SQLite 则承担业务数据和 AI 配置数据的持久化存储任务。

    在系统接入层面，backend/app/main.py 统一挂载了普通教务路由、管理员 AI 路由、AI Portal 路由和 AI QA 路由，并通过 /api 前缀形成统一接口出口。该设计在兼顾历史路由兼容性的同时，保持了前端访问方式的一致性。前端学生端与教师端共用 streamQA 核心请求函数，通过传入模型标识、课程编号与工作流 code，将问题提交至 /api/ai_qa/qa/stream，由后端根据业务场景完成解析与处理。
    """)
    add_figure(doc, assets["system_arch"], "图2-1  系统总体架构图", width_cm=16.2)

    add_heading2(doc, "2.5 AI 闭环设计与答辩主线映射")
    add_paragraphs(doc, """
    结合开题与答辩材料，本文将系统的 AI 实现主线概括为“配置端—业务端—数据回流—持续优化”的闭环结构。其中，配置端对应管理员对模型 API、知识库与工作流的统一编排；业务端对应学生与教师在具体页面中调用 AI 能力；数据回流体现为日志、任务状态、知识文档与课程资料在系统中的持续沉淀；持续优化则依据使用效果不断调整模型选择、知识来源与流程策略。该闭环表明，系统中的 AI 能力并非附着于页面表层的附加功能，而是可配置、可接入、可追踪、可优化的业务能力集合。

    为支撑上述闭环，系统进一步抽象出 AI 配置编排层、知识组织层、推理执行层和业务接入层四层结构。配置编排层负责模型选择、知识库绑定与工作流调度；知识组织层负责将教师和管理员上传的资料转化为机器可检索的文本分块；推理执行层负责检索相关片段、组装 Prompt、调用模型并完成流式返回；业务接入层则保障 AI 客服、AI 课程助手与智能教案等场景能够在多角色页面中被实际访问和使用。该分层结构构成后续系统实现分析的逻辑基础。
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
    从项目实际实现情况看，前端最终采用 Vue3、TypeScript 与 Element Plus 组合，而未完全沿用开题报告中预期的 Vuetify 方案。该调整体现了开发过程中的工程化取舍：其一，Element Plus 与后台管理类页面中的表格、表单和弹窗组件适配度较高，更适合承接教务系统中高频的数据录入与展示场景；其二，项目原有页面结构与相关生态资源更便于在 Vue3 + Element Plus 体系下持续扩展。因此，虽然最终实现与最初设想存在差异，但其与项目真实落地状态更为一致。

    后端方面，FastAPI 依托异步接口模型、自动文档能力和依赖注入机制，能够较好地承载多角色业务接口与 AI 相关接口。SQLAlchemy 为系统提供统一的 ORM 抽象，使普通业务表与 AI 相关数据表能够在同一会话管理体系下完成读写；SQLite 则满足毕业设计阶段轻量部署和本地联调的要求。此外，requirements.txt 中引入 scikit-learn、pypdf、pandas 等依赖，用于支撑知识文档抽取、轻量检索与数据处理任务。综合来看，该技术栈在实现复杂度、学习成本与演示可行性之间取得了较为合理的平衡 [4][5][6]。
    """)

    add_heading2(doc, "3.2 AI 工作流、知识库与文档处理机制")
    add_paragraphs(doc, """
    本系统的 AI 能力并非建立在单一聊天页面之上，而是依托后台抽象出的工作流应用、模型 API 与知识库对象协同实现。管理员通过 admin_ai.py 中的相关接口维护 ai_model_apis、ai_knowledge_bases 和 ai_workflow_apps 三类核心对象。其中，模型 API 用于记录模型名称、供应商、接口地址、密钥、超时与温度等参数；知识库对象通过 owner_type、course_id、feature 等字段区分系统级知识库、课程级知识库及不同功能场景；工作流应用则负责将模型与知识库进行绑定，并以 code 区分 AI 客服、AI 课程助手和智能教案等业务入口。

    知识库能够实际参与检索，依赖于文档上传与文本分块机制。根据 services/ai_workflow.py 的实现，系统支持从 txt、md、csv、pdf、docx、xlsx 等多种文件类型中提取文本。抽取得到的内容首先进行换行与格式规范化处理，随后按照默认 450 字符块大小和 80 字符重叠量切分为多个 chunk。每个 chunk 除正文内容外，还记录 token 数、文档标题、文档 URL、所属知识库和所属文档等元数据，并最终写入 ai_kb_chunks 表。通过这一处理过程，上传文档被转化为后续问答可调用、可追踪的数据资源。

    教师侧课程知识库与管理员侧基础知识库并非简单复制关系，而是通过 owner_user_id 与 course_id 等字段体现所有权与课程归属。教师在 CourseAssistant.vue 与 LessonPlan.vue 中上传课程资料时，后端首先验证课程是否属于当前教师，随后确保对应课程知识库对象存在，再完成文件保存、文本抽取与 chunk 重建。该流程贯穿权限校验、知识组织和数据更新等环节，使 AI 课程助手与智能教案具备按课程、按教师和按场景运行的基础条件。
    """)

    add_heading2(doc, "3.3 轻量级检索增强生成实现")
    add_paragraphs(doc, """
    在问答与教案生成链路中，知识库价值最终通过检索增强生成机制体现。项目当前未引入向量数据库，而是采用适用于毕业设计阶段的轻量级 RAG 方案。具体而言，后端在 retrieve_top_chunks 函数中首先获取目标知识库的 chunk 集合，随后利用 scikit-learn 中的 TfidfVectorizer 构建问题与文本片段的特征表示，再通过 cosine_similarity 计算相似度并筛选 Top-K 结果。被召回的片段在 _build_prompt 函数中被组织为带编号的上下文，并与用户问题共同组装为最终 Prompt 发送给模型。

    该实现方案具有较明显的工程优势。首先，其依赖较为简单，无需额外部署向量服务，适合在单机环境中快速完成部署与演示；其次，检索过程清晰，便于说明文档如何被拆分、召回和拼接；再次，对于中小规模知识库而言，TF-IDF 方案具有较高的工程性价比。从当前数据库统计结果看，截至2026年4月24日，系统中共包含 86 个 chunk，该数据规模能够支撑轻量级检索方案有效运行。

    同时，该方案亦存在客观局限。由于 TF-IDF 更依赖关键词匹配，对于同义表达、长文本语义关联和跨文档概念召回的处理能力有限；此外，系统当前主要将工作流知识库与课程知识库合并后统一计算相似度，尚未在算法层面对课程私有知识优先级建立更严格的排序约束。因此，本文在后续展望中将向量检索、混合检索和引用追踪列为重点优化方向，这也与答辩材料中提出的“轻量落地、逐步演进”的实现思路保持一致。
    """)

    add_heading2(doc, "3.4 模型选择优先级与 SSE 流式响应机制")
    add_paragraphs(doc, """
    在模型调用方面，ai_qa.py 实现了较为明确的优先级策略。首先，当请求参数中显式传入 model 标识时，后端优先解析并检索处于启用状态的目标模型；其次，若工作流本身绑定了 model_api_id，则使用工作流关联模型；最后，若前两种方式均未获取到可用模型，系统回退至已启用且优先级最高的默认模型。该策略保证了统一推理入口下的场景差异化配置能力。

    鉴于大模型响应存在一定生成时延，系统采用 Server-Sent Events 作为前后端流式通信机制。前端通过 streamQA 函数向 /api/ai_qa/qa/stream 发起 POST 请求，并在收到 text/event-stream 响应后按分帧规则解析数据块；后端则在 _call_model_api 中将模型输出拆分为多个片段，以 SSE 事件形式持续返回前端。该实现虽然未引入 WebSocket，但已能够满足当前 AI 问答与生成场景下的单向流式输出需求，并有效改善用户等待体验。

    此外，系统已经支持 DashScope OpenAI 兼容接口与 Ark Responses 两类 provider，说明模型接入层已具备一定的抽象与兼容能力。管理员端页面进一步提供了模型连通性测试入口，可在保存配置前验证 endpoint、api_key 与 model_name 的有效性。对于毕业设计项目而言，这一“模型配置—接口测试—业务调用”的完整链路体现了系统已具备基本的工程可运维特征。
    """)

    add_heading2(doc, "3.5 数据库设计与核心表结构")
    add_paragraphs(doc, f"""
    数据库设计是连接教务业务逻辑与 AI 能力实现的关键环节。项目当前以 SQLite 作为底层数据库，在普通业务表之外，围绕 AI 功能扩展了模型 API 表、知识库表、知识库文档表、知识库分块表、工作流应用表、教案任务表、课程 AI 收藏与选择表以及 AI 使用日志表等结构。上述数据表不仅记录配置参数，也保存运行状态与生成结果，使系统中的 AI 行为具备可追踪、可复盘和可再利用的基础条件。

    截至{CHECK_DATE_CN}，本地数据库中已有 {counts.get("ai_model_apis", 0)} 条模型 API 配置、{counts.get("ai_knowledge_bases", 0)} 个知识库、{counts.get("ai_kb_documents", 0)} 份知识库文档、{counts.get("ai_kb_chunks", 0)} 个分块片段、{counts.get("ai_workflow_apps", 0)} 个工作流应用、{counts.get("ai_lesson_plan_tasks", 0)} 条教案任务记录，以及 {data.get("usage_log_count", 0)} 条 AI 使用日志。上述样本表明，系统不仅完成了数据结构设计，还已形成可供分析与验证的实际运行数据。
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
    从代码目录结构来看，后端采用 models、routers、schemas、services、dependencies 等分层组织方式，前端则以 views、components、api、stores 和 router 等目录组织页面、组件与交互逻辑。该结构使基础业务功能与 AI 功能既能够并行扩展，又可以通过统一依赖机制共享用户认证、数据库连接和静态资源访问方式。例如，backend/app/main.py 在系统启动时统一注册 ai_qa、ai_portal、admin_ai 等 AI 相关路由，并保留课程、请假、办事大厅、证书和消息等基础业务路由，从而保证 AI 能力始终建立在完整的教务框架之上。

    前端的角色化组织亦较为清晰。学生端页面主要提供课程查询、办事大厅和 AI 课程助手等入口；教师端进一步提供知识库维护、课程助手自定义和智能教案任务管理等功能；管理员端通过 AdminAIConfig.vue 集中管理模型、知识库和工作流绑定关系。值得注意的是，AI 客服组件并非以独立实验页面存在，而是通过 Layout.vue 在学生端和教师端统一挂载，表明该模块被定位为平台级公共服务能力。
    """)

    add_heading2(doc, "4.2 AI 客服逻辑与代码实现")
    add_paragraphs(doc, """
    AI 客服是系统中最贴近校园服务入口的智能模块。前端 StudentAIChat.vue 与 TeacherAIChat.vue 在组件挂载阶段分别请求 /ai/customer-service/config 和 /ai/customer-service/apps 接口，以加载欢迎语、推荐问题、输入提示语以及当前可用的客服工作流。用户提交问题后，组件统一调用 streamQA 方法，将 workflow code、user_id 与问题文本发送至 /api/ai_qa/qa/stream。与此同时，组件内部还维护本地多会话列表、浮动窗口位置和未读状态等交互逻辑，从而保证该模块在可用性层面具备较完整的交互支撑。

    后端 AI 客服的核心处理逻辑集中于 ai_qa.py。系统首先通过 _load_workflow_app 根据 workflow code 获取工作流对象，随后通过 _resolve_model 按“请求指定模型—工作流绑定模型—已启用默认模型”的顺序解析实际调用模型；接着，_collect_kb_ids 收集工作流知识库与课程知识库编号，_build_prompt 基于 retrieve_top_chunks 召回的文本片段组装 Prompt，最后由 _call_model_api 按 provider 类型调用外部模型接口，并将结果拆分为 SSE 数据块返回前端。该处理流程说明，前端界面并不直接依赖具体模型实现，后端亦未将知识库、模型和业务场景硬编码绑定，而是通过工作流机制完成解耦与协调。

    从业务应用角度分析，AI 客服适用于请假流程说明、选课规则解释、成绩查询入口指引以及办事事项咨询等高频问题场景。其主要优势在于接入路径统一、响应形式友好、配置方式灵活，并能够随着知识库内容补充逐步提升回答质量。由于系统仍保留普通办事大厅、请假和课程等基础业务模块，AI 客服在整体架构中更适合作为业务解释层，以增强用户对流程规则的理解能力。

    结合代码复查结果可知，该模块仍存在若干需要完善之处。第一，settings_json 中虽然保留了 system_prompt_template 配置项，但当前 _build_prompt 尚未将该模板注入最终 Prompt；第二，_load_workflow_app 目前主要按 code 直接查询，缺少对工作流启用状态的严格执行层校验，因此已禁用工作流在特定情况下仍可能被访问；第三，前端虽已传递 history_flag，但主链路尚未形成稳定的多轮记忆机制。这些问题不影响模块主流程运行，但对系统进一步提升稳定性与治理一致性具有重要影响。
    """)
    add_figure(doc, assets["flow_customer"], "图4-1  AI 客服核心处理流程", width_cm=16.0)
    add_figure(doc, assets["shot_customer"], "图4-2  AI 客服界面截图占位（后续替换）", width_cm=15.5)

    add_heading2(doc, "4.3 AI 课程助手逻辑与代码实现")
    add_paragraphs(doc, """
    AI 课程助手的设计目标在于使问答内容尽可能贴近具体课程与教师提供的真实资料，从而提升回答的针对性和教学适配度。学生端 StudentCourseAssistant.vue 的实现相对简洁：页面加载时调用 /ai/course-assistant/apps 接口获取已启用的课程助手工作流列表，学生选择某一助手并输入问题后，仍通过统一的 streamQA 接口完成流式问答。该设计有效提高了前端逻辑复用度，并使学生侧无需直接感知模型与知识库的底层细节。

    教师端 CourseAssistant.vue 则更集中地体现了该模块的工程价值。页面初始化阶段会并行加载教师课程列表、管理员提供的基础课程助手工作流以及教师已创建的个人工作流。教师可基于基础工作流复制生成新的课程助手，并对其关联课程、名称和模型配置进行调整，同时通过 /ai/teacher/kb/upload 上传课程私有知识文档。文档上传完成后将被纳入课程知识库，从而为后续课程问答提供更具针对性的知识支撑。

    后端方面，ai_portal.py 提供了课程助手的公共接口与教师专属接口。其中，/course-assistant/apps 用于向学生端和教师端返回当前可用的启用工作流；/teacher/course-assistant/apps 则支持教师对个人课程助手工作流进行获取、创建、修改与删除。教师上传课程文档时，系统会根据 teacher_user_id 与 course_id 自动确保相应知识库对象存在，并完成文件保存、文本抽取与 chunk 更新。由此，AI 课程助手形成了“管理员提供基础能力、教师补充课程资料、学生围绕课程提问”的完整业务闭环。

    需要指出的是，界面设计与功能说明强调“教师知识库优先、基础知识库兜底”的应用意图，表明系统期望优先发挥课程私有资料的作用。但从当前 ai_qa.py 的实现逻辑看，工作流知识库与课程知识库更多以合并方式参与轻量检索，尚未在算法层面建立更强的优先级约束。因此，可以认为该模块已经完成课程知识增强的基础实现，但仍有必要在后续迭代中引入课程知识优先级、来源权重与引用展示等更精细的检索策略。
    """)
    add_figure(doc, assets["flow_course"], "图4-3  AI 课程助手核心处理流程", width_cm=16.0)
    add_figure(doc, assets["shot_course"], "图4-4  AI 课程助手界面截图占位（后续替换）", width_cm=15.5)

    add_heading2(doc, "4.4 智能教案逻辑与代码实现")
    add_paragraphs(doc, """
    与 AI 客服和 AI 课程助手相比，智能教案模块更强调生成任务的管理属性，而非单次问答交互。LessonPlan.vue 页面加载时会获取公共模型列表、教师授课课程、课程知识库文档以及历史教案任务。教师在使用过程中先选定课程，再从课程知识库中选择文档进行解析，填写教案标题与大纲内容，随后通过 createLessonPlanTask 创建任务记录。实际的教案生成并不由任务创建接口直接完成，而是通过统一的 streamQA 接口调用 lesson_plan 工作流实现。该设计既复用了底层推理链路，也使任务状态得以独立维护。

    当教案生成完成后，前端会将拼接得到的 Markdown 文本通过 updateLessonPlanTaskResult 回写至后端，更新任务状态为 completed 并保存结果内容。教师还可在页面中继续编辑生成结果、再次保存修改或导出为 Markdown 文件。由此可见，系统并未将 AI 定位为一次性文本输出工具，而是将其作为教案初稿生成器，再由教师完成人工修订和最终确认。这种“AI 辅助生成—教师审校完善”的模式更符合真实教学场景下的责任边界要求。

    从数据库结构看，ai_lesson_plan_tasks 表记录了教师编号、课程编号、标题、大纲、状态、结果、错误信息、知识库编号和模型编号等字段，能够较完整地描述一次教案生成任务从创建到完成的生命周期。此外，系统在创建教案任务时同步写入 AiUsageLog，说明教案生成过程已被纳入统一的 AI 使用统计体系。与仅返回单段文本的方案相比，该任务化、状态化和日志化设计更具工程组织意义。

    结合代码分析，当前模块仍存在若干可优化细节。例如，前端 parseSelectedDoc 对 txt、md、csv 等文本文件能够直接拉取内容并填入大纲，但对于 docx、pdf 等文件仍主要依赖上传阶段的后端预处理，界面层“解析结果”展示尚有提升空间；同时，教案质量评价当前主要依赖教师人工判断，缺乏自动化结构校验、教学目标完整性检查和引用来源提示机制。上述问题并不影响模块的基本可用性，但为后续迭代提供了明确方向。
    """)
    add_figure(doc, assets["flow_lesson"], "图4-5  智能教案任务化生成流程", width_cm=16.0)
    add_figure(doc, assets["shot_lesson"], "图4-6  智能教案界面截图占位（后续替换）", width_cm=15.5)

    add_heading2(doc, "4.5 管理端 AI 配置实现")
    add_paragraphs(doc, """
    管理员端的核心价值在于将模型、知识库与工作流从具体业务页面中抽离，形成统一的后台治理入口。AdminAIConfig.vue 页面以标签页方式组织模型 API 管理、知识库管理和工作流管理三类区域。管理员可以新增或编辑模型名称、provider、endpoint、api_key、温度、最大输出长度与默认状态等参数，也可以通过手动测试弹窗直接调用模型接口，以验证配置连通性。该能力为系统提供了基本的环境切换与问题定位手段。

    在知识库管理方面，管理员能够创建工作流知识库、上传文档并触发 chunk 重建。后端 admin_ai.py 中的相关接口除完成文件保存外，还对文档数量和 chunk 数量进行统计，便于管理员掌握知识库规模与更新情况。在工作流管理方面，管理员可为 AI 客服、AI 课程助手和智能教案等不同类型工作流绑定知识库、模型 API 与状态，并维护欢迎语、提示语和推荐问题等界面参数。当前前端将这些场景化参数写入 app.settings_json，从而保持用户端读取配置与工作流绑定关系的一致性。

    需要指出的是，项目代码中仍可见 AiFeatureSetting 等补充配置结构，但用户侧实际读取逻辑更多集中于 AiWorkflowApp.settings_json。这一现象说明系统在开发过程中逐步由功能级设置向工作流级设置收敛，当前实现已呈现出以工作流为核心的管理思路。对于论文分析而言，这种结构演进本身具有研究价值，反映了系统在开发过程中围绕可维护性和配置一致性所进行的持续调整。
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
    综合分析表明，本项目的主要特点并不在于单一算法复杂度，而在于将 AI 能力嵌入到了完整的教务业务体系之中。首先，系统以工作流、知识库和模型 API 为核心完成统一抽象，使不同 AI 模块能够复用同一套底层问答与生成机制；其次，系统同时覆盖学生即时咨询、教师课程资料管理和任务化教案生成等场景，体现出多角色协同的业务价值；再次，数据库不仅保存配置数据，还保存任务记录、文档分块和使用日志，为后续分析与系统演进提供了数据基础。

    与此同时，项目仍存在若干客观不足。其一，AI 客服配置中的 system_prompt_template 尚未真正参与问答 Prompt 组装，说明管理员配置尚未完全映射至执行层；其二，工作流状态校验仍有加强空间，需避免已禁用工作流被直接按 code 调用；其三，前端虽然维护多会话信息，但后端主链路尚未形成稳定的多轮记忆使用机制；其四，自动化测试脚本未能与当前接口保持完全同步；其五，知识检索仍以 TF-IDF 为主，在复杂语义场景下存在提升空间。上述问题均可在代码层面定位，为后续修复和优化提供了明确依据。
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
    本文在测试设计上并未将重点放在大规模压力数据上，而是围绕毕业设计答辩阶段最需要验证的关键事实展开。对于 AI 模块而言，核心问题主要包括：页面加载时能否正确获取配置，提问或生成请求能否进入真实后端链路，以及生成结果能否完成落库并被再次读取。因此，测试重点集中于配置接口、工作流接口、统一问答接口、课程助手创建接口和教案任务接口，以验证系统主链路的完整性与可运行性。

    测试环境基于项目本地仓库构建完成。后端运行于 Python 3.13.13 与项目 .venv 虚拟环境中，前端运行于 Node.js v22.19.0 环境中。Windows 启动脚本 start_project.bat 已对 uvicorn 服务、Vite 开发服务和浏览器自动打开流程进行了串联，说明项目已具备相对完整的本地演示闭环。

    为降低真实模型调用额度与外部网络波动对验证结果的干扰，本文在接口联调中采用内存数据库结合模拟模型返回值的方式开展验证。该方法并非回避真实调用，而是将测试重点聚焦于项目内部逻辑本身，以便更准确地观察工作流查找、知识库编号收集、任务创建和结果回写等关键步骤是否能够正常执行。
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
    联调结果的主要价值在于验证了三个表面上相互独立的应用场景实际上共享同一套底层能力链路。AI 客服能够完成配置读取与流式问答，说明工作流配置和问答接口之间的连接是有效的；教师能够创建课程助手，说明管理员提供的基础工作流已能够向教师场景继续分发；教案任务能够创建并完成结果回写，则说明系统不仅可以生成文本，还能够对生成行为进行结构化管理。综合这些结果可知，系统中的 AI 功能已形成建立在统一数据结构和统一接口机制之上的模块化能力体系。

    联调结果还反映出系统具有较强的底层复用特征。无论是客服咨询、课程答疑还是教案生成，最终均回归到模型解析、知识检索、流式输出和结果持久化等核心处理环节。对于毕业设计项目而言，这种复用结构不仅降低了实现复杂度，也为后续扩展新的 AI 场景提供了可直接继承的基础设施条件。
    """)

    add_heading2(doc, "5.3 自动化测试现状与发现的问题")
    add_paragraphs(doc, """
    在对现有测试脚本进行复查时，本文执行了 backend/tests/test_ai_customer_service_stream.py。结果显示，截至2026年4月24日，该测试未能通过，主要原因包括两个方面：其一，fixture 中直接使用 monkeypatch 变量而未将其作为参数传入，导致测试在执行阶段出现 NameError；其二，测试脚本访问的接口路径仍为 /api/ai_qa/customer-service/stream，而当前实际生效的流式问答接口已调整为 /api/ai_qa/qa/stream。该结果表明，项目虽然已具备较好的接口联调基础，但自动化测试脚本尚未与代码重构保持同步。

    此外，在运行测试脚本过程中还出现了多项 Pydantic V2 兼容性提示以及 FastAPI on_event 弃用警告。上述警告虽然不会直接阻断系统启动，但从软件工程视角看，反映出项目在依赖升级后的代码规范迁移方面仍有完善空间。对于毕业设计答辩而言，这些问题可作为工程优化方向进行客观说明；对于后续持续迭代而言，则应尽快完成旧式 validator、orm_mode 以及启动事件写法的迁移与清理。
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
    综合分析表明，本系统已经完成毕业设计答辩所需的主要 AI 链路验证。无论是管理员端配置治理、学生端智能咨询，还是教师端课程知识上传与任务化教案生成，均已具备明确的代码入口、数据库落点和较完整的流程结构。特别是 AI 客服、AI 课程助手与智能教案三条链路之间共享的底层设计，表明项目并非简单叠加功能，而是在尝试构建面向高校教务场景的统一 AI 能力底座。

    当然，系统评价仍需区分“具备可用性”与“达到完善状态”两个层面。接口联调通过并不意味着系统已经覆盖所有真实网络环境、浏览器交互细节和异常分支场景；自动化测试脚本未及时更新亦说明工程保障能力仍待加强。因此，本文认为该系统已达到“主链路可运行、核心功能可演示、现存问题可定位”的阶段，可作为毕业设计成果提交，并为后续持续完善提供可靠基础。
    """)

    add_heading1(doc, "第六章 总结与展望")
    add_heading2(doc, "6.1 全文总结")
    add_paragraphs(doc, """
    本文的核心工作在于基于已有代码基础，对高校教务系统中的 AI 模块进行系统梳理、结构分析与运行验证，并据此形成与功能、接口、数据和测试结果相对应的毕业论文内容。通过对前端页面、后端路由、数据库样本和接口联调结果的综合分析，本文阐明了系统如何将 AI 客服、AI 课程助手和智能教案三类能力嵌入原有教务流程，并进一步说明了其背后的工作流组织、知识库支撑与任务管理结构。

    从当前实现结果看，项目已呈现出三个较为明确的工程特征：其一，AI 模块具备统一底座，不同业务场景能够复用同一套模型选择与问答处理主链路；其二，知识库已经从单纯文件上传扩展为可抽取、可分块、可检索的数据资源；其三，教案生成并非一次性文本输出，而是被纳入任务创建、结果回写和后续编辑的完整过程。对毕业设计而言，这种从代码实现到论文论证的对应关系，能够更充分体现系统分析与工程实现的完整性。
    """)

    add_heading2(doc, "6.2 后续展望")
    add_paragraphs(doc, """
    后续完善方向可概括为两个层面。第一是补齐现有实现缺口，包括使 system_prompt_template 真正参与 Prompt 组装、在执行层严格校验工作流启用状态、将多会话历史与后端记忆链路有效对接、更新失效测试脚本并完成依赖兼容性警告的清理。第二是提升系统能力上限，例如将当前轻量检索逐步升级为混合检索或向量检索，为教案结果增加结构化质量检查机制，并为问答结果建立评分、抽样复核与来源提示机制。

    从更长远的视角看，AI 在高校教务系统中的作用不应局限于替代人工回复，而应成为连接规则解释、课程支持与教学内容生产的辅助层。当前项目已初步验证了该方向在工程实现上的可行性，即只要模型能力、知识来源与业务入口之间的关系得到清晰设计，AI 便能够稳定服务于教务场景。未来系统迭代的重点，不应仅停留在模型接入数量的增加，更应关注回答准确性、过程可追踪性以及整体运维稳定性的持续提升。
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
