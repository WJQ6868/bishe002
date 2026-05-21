# -*- coding: utf-8 -*-
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path(r"D:\bishe\one\generated\thesis_assets\fig_3_1_ai_architecture_code_api_design_v2.png")
W, H = 3200, 1080
BG = "white"
BLACK = (20, 20, 20)
LINE = (35, 35, 35)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    for fp in candidates:
        path = Path(fp)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    raise RuntimeError("No Chinese font found")


TITLE_FONT = load_font(48)
HEAD_FONT = load_font(36)
SMALL_FONT = load_font(20)
LABEL_FONT = load_font(24)


img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

title = "AI模块架构、代码组织与接口关系图"
title_box = draw.textbbox((0, 0), title, font=TITLE_FONT)
title_w = title_box[2] - title_box[0]
draw.text(((W - title_w) / 2, 24), title, fill=BLACK, font=TITLE_FONT)

left = 86
top = 105
box_w = 560
gap = 42
header_h = 88
box_h = 700
radius = 20

boxes = [
    {
        "title": "角色与场景层",
        "lines": [
            "学生",
            "AI客服、课程问答",
            "",
            "教师",
            "课程助手、智能教案",
            "",
            "管理员",
            "模型、知识库、工作流配置",
            "",
            "核心问题",
            "谁来用、从哪进",
        ],
        "font_size": 30,
    },
    {
        "title": "前端页面与代码组织",
        "lines": [
            "AdminAIConfig.vue",
            "CourseAssistant.vue",
            "LessonPlan.vue",
            "StudentAIChat.vue",
            "StudentCourseAssistant.vue",
            "adminAi.ts",
            "aiPortal.ts",
            "ai.ts",
        ],
        "font_size": 28,
    },
    {
        "title": "后端接口层",
        "lines": [
            "admin_ai.py / ai_portal.py",
            "/admin/ai/model-apis",
            "/admin/ai/workflows/apps",
            "/admin/ai/workflows/knowledge-bases",
            "/ai/customer-service/config",
            "/ai/course-assistant/apps",
            "/ai/teacher/kb/upload",
            "/ai/teacher/lesson-plan/tasks",
            "ai_qa.py / ai_qa/qa/stream",
        ],
        "font_size": 24,
    },
    {
        "title": "AI能力编排层",
        "lines": [
            "工作流确定场景入口",
            "模型优先级选择",
            "文档抽取与规范化",
            "文本分块与知识整理",
            "TF-IDF检索与上下文组装",
            "SSE流式输出",
            "结果回写与状态保留",
        ],
        "font_size": 30,
    },
    {
        "title": "数据与资源层",
        "lines": [
            "ai_model_apis",
            "ai_knowledge_bases",
            "ai_kb_documents",
            "ai_kb_chunks",
            "ai_workflow_apps",
            "ai_lesson_plan_tasks",
            "ai_usage_logs",
        ],
        "font_size": 28,
    },
]

connector_labels = ["场景进入", "页面调用", "接口调度", "数据支撑"]


def draw_centered_block(
    draw_obj: ImageDraw.ImageDraw,
    area: tuple[int, int, int, int],
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    *,
    gap_px: int = 8,
    fill_height: bool = False,
    gap_min: int = 8,
    gap_max: int = 44,
) -> None:
    x1, y1, x2, y2 = area
    rows: list[tuple[str, int, int] | None] = []
    heights: list[int] = []
    for line in lines:
        if not line:
            rows.append(None)
            heights.append(font.size // 2)
            continue
        box = draw_obj.textbbox((0, 0), line, font=font)
        w = box[2] - box[0]
        h = box[3] - box[1]
        rows.append((line, w, h))
        heights.append(h)
    row_count = len(lines)
    if fill_height and row_count > 1:
        free_h = (y2 - y1) - sum(heights)
        gap_px = max(gap_min, min(gap_max, int(free_h / (row_count - 1))))
    total_h = sum(heights) + max(0, row_count - 1) * gap_px
    y = y1 + max(0, (y2 - y1 - total_h) / 2)
    for i, row in enumerate(rows):
        if row is None:
            y += heights[i] + gap_px
            continue
        line, w, h = row
        x = x1 + (x2 - x1 - w) / 2
        draw_obj.text((x, y), line, fill=BLACK, font=font)
        y += h + gap_px


for idx, box in enumerate(boxes):
    x1 = left + idx * (box_w + gap)
    y1 = top
    x2 = x1 + box_w
    y2 = y1 + box_h

    draw.rounded_rectangle((x1, y1, x2, y2), radius=radius, outline=LINE, width=4, fill="white")
    draw.line((x1, y1 + header_h, x2, y1 + header_h), fill=LINE, width=4)

    header_box = draw.textbbox((0, 0), box["title"], font=HEAD_FONT)
    header_w = header_box[2] - header_box[0]
    header_h_text = header_box[3] - header_box[1]
    draw.text(
        (x1 + (box_w - header_w) / 2, y1 + (header_h - header_h_text) / 2 - 2),
        box["title"],
        fill=BLACK,
        font=HEAD_FONT,
    )

    body_font = load_font(box["font_size"])
    draw_centered_block(
        draw,
        (x1 + 22, y1 + header_h + 16, x2 - 22, y2 - 18),
        box["lines"],
        body_font,
        gap_px=10,
        fill_height=True,
        gap_min=10,
        gap_max=42,
    )


base_y = top + box_h + 46
for i, label in enumerate(connector_labels):
    x_a = left + box_w * (i + 1) + gap * i
    x_b = left + box_w * (i + 1) + gap * (i + 1)
    x_mid = (x_a + x_b) / 2
    draw.line((x_a + 8, base_y, x_b - 36, base_y), fill=LINE, width=3)
    draw.polygon([(x_b - 36, base_y - 10), (x_b - 36, base_y + 10), (x_b - 6, base_y)], fill=LINE)
    label_box = draw.textbbox((0, 0), label, font=LABEL_FONT)
    label_w = label_box[2] - label_box[0]
    draw.text((x_mid - label_w / 2, base_y - 38), label, fill=BLACK, font=LABEL_FONT)


note_lines = [
    "说明：该图将角色入口、前端页面、接口分组、AI能力与底层数据放到同一条设计链上，",
    "用于说明结构关系、代码组织与接口协同方式。",
]
draw_centered_block(draw, (120, H - 86, W - 120, H - 18), note_lines, SMALL_FONT, gap_px=4)

img.save(OUT, quality=96)
print(OUT)
