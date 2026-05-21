from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "generated" / "thesis_assets"
FONT_REGULAR = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_BOLD = Path(r"C:\Windows\Fonts\simhei.ttf")
FONT_MONO = Path(r"C:\Windows\Fonts\consola.ttf")
FONT_MONO_BOLD = Path(r"C:\Windows\Fonts\consolab.ttf")


@dataclass
class BoxSpec:
    x: int
    y: int
    w: int
    h: int
    title: str
    lines: list[str]

    @property
    def rect(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)


def is_ascii_only(text: str) -> bool:
    return all(ord(ch) < 128 for ch in text)


def load_font(size: int, *, bold: bool = False, ascii_only: bool = False) -> ImageFont.FreeTypeFont:
    if ascii_only:
        font_path = FONT_MONO_BOLD if bold and FONT_MONO_BOLD.exists() else FONT_MONO
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=size)
    font_path = FONT_BOLD if bold and FONT_BOLD.exists() else FONT_REGULAR
    return ImageFont.truetype(str(font_path), size=size)


def measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top


def fit_font(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    max_width: int,
    max_height: int,
    *,
    max_size: int,
    min_size: int,
    bold: bool = False,
    gap_ratio: float = 0.30,
) -> tuple[ImageFont.FreeTypeFont, int]:
    ascii_only = all(is_ascii_only(line) for line in lines if line)
    for size in range(max_size, min_size - 1, -1):
        font = load_font(size, bold=bold, ascii_only=ascii_only)
        widths: list[int] = []
        heights: list[int] = []
        for line in lines:
            width, height = measure_text(draw, line, font)
            widths.append(width)
            heights.append(height)
        gap = max(6, int(size * gap_ratio))
        total_height = sum(heights) + gap * (len(lines) - 1)
        if max(widths, default=0) <= max_width and total_height <= max_height:
            return font, gap
    return load_font(min_size, bold=bold, ascii_only=ascii_only), max(6, int(min_size * gap_ratio))


def draw_centered_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    box: tuple[int, int, int, int],
    *,
    font: ImageFont.FreeTypeFont,
    gap: int,
    fill: str = "black",
) -> None:
    x1, y1, x2, y2 = box
    heights = [measure_text(draw, line, font)[1] for line in lines]
    total_height = sum(heights) + gap * (len(lines) - 1)
    y = y1 + (y2 - y1 - total_height) / 2
    for line, height in zip(lines, heights):
        width, _ = measure_text(draw, line, font)
        x = x1 + (x2 - x1 - width) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += height + gap


def draw_entity_box(
    draw: ImageDraw.ImageDraw,
    spec: BoxSpec,
    *,
    title_max: int,
    title_min: int,
    body_max: int,
    body_min: int,
) -> None:
    x1, y1, x2, y2 = spec.rect
    pad_x = 18
    pad_y = 16
    line_width = 4
    header_height = max(60, int(spec.h * 0.24))
    draw.rectangle(spec.rect, outline="black", fill="white", width=line_width)
    draw.line((x1, y1 + header_height, x2, y1 + header_height), fill="black", width=line_width)

    title_font, title_gap = fit_font(
        draw,
        [spec.title],
        spec.w - pad_x * 2,
        header_height - pad_y * 2,
        max_size=title_max,
        min_size=title_min,
        bold=True,
        gap_ratio=0.15,
    )
    draw_centered_lines(
        draw,
        [spec.title],
        (x1 + pad_x, y1 + pad_y, x2 - pad_x, y1 + header_height - pad_y),
        font=title_font,
        gap=title_gap,
    )

    body_font, body_gap = fit_font(
        draw,
        spec.lines,
        spec.w - pad_x * 2,
        spec.h - header_height - pad_y * 2,
        max_size=body_max,
        min_size=body_min,
        bold=False,
        gap_ratio=0.28,
    )
    draw_centered_lines(
        draw,
        spec.lines,
        (x1 + pad_x, y1 + header_height + pad_y, x2 - pad_x, y2 - pad_y),
        font=body_font,
        gap=body_gap,
    )


def draw_diamond(
    draw: ImageDraw.ImageDraw,
    *,
    cx: int,
    cy: int,
    w: int,
    h: int,
    text: str,
) -> None:
    points = [(cx, cy - h // 2), (cx + w // 2, cy), (cx, cy + h // 2), (cx - w // 2, cy)]
    draw.polygon(points, outline="black", fill="white", width=4)
    font, gap = fit_font(draw, [text], w - 28, h - 28, max_size=42, min_size=26, bold=True, gap_ratio=0.10)
    draw_centered_lines(draw, [text], (cx - w // 2 + 10, cy - h // 2 + 10, cx + w // 2 - 10, cy + h // 2 - 10), font=font, gap=gap)


def draw_label(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, *, size: int = 24) -> None:
    font = load_font(size, bold=True, ascii_only=is_ascii_only(text))
    width, height = measure_text(draw, text, font)
    box = (x - width // 2 - 8, y - height // 2 - 4, x + width // 2 + 8, y + height // 2 + 4)
    draw.rectangle(box, fill="white")
    draw.text((box[0] + 8, box[1] + 4), text, font=font, fill="black")


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], *, width: int = 4) -> None:
    draw.line([start, end], fill="black", width=width)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if dx == 0 and dy == 0:
        return
    if abs(dx) >= abs(dy):
        step = 16
        direction = 1 if dx > 0 else -1
        arrow = [(end[0], end[1]), (end[0] - direction * step, end[1] - 7), (end[0] - direction * step, end[1] + 7)]
    else:
        step = 16
        direction = 1 if dy > 0 else -1
        arrow = [(end[0], end[1]), (end[0] - 7, end[1] - direction * step), (end[0] + 7, end[1] - direction * step)]
    draw.polygon(arrow, fill="black")


def draw_poly_arrow(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], *, width: int = 4) -> None:
    for start, end in zip(points, points[1:]):
        draw.line([start, end], fill="black", width=width)
    draw_arrow(draw, points[-2], points[-1], width=width)


def generate_role_er(path: Path) -> None:
    width, height = 2000, 1080
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    outer = (60, 60, 1940, 1020)
    draw.rectangle(outer, outline="black", width=5)
    label_font = load_font(28, bold=True)
    draw.text((90, 88), "AI赋能高校教务系统", font=label_font, fill="black")

    left_boxes = [
        BoxSpec(160, 170, 300, 170, "学生", ["角色实体"]),
        BoxSpec(160, 450, 300, 170, "教师", ["角色实体"]),
        BoxSpec(160, 730, 300, 170, "管理员", ["角色实体"]),
    ]
    right_boxes = [
        BoxSpec(1030, 120, 760, 230, "学生侧需求实体", ["课程查询与办理", "AI客服咨询", "课程答疑支持"]),
        BoxSpec(1030, 400, 760, 230, "教师侧需求实体", ["课程资料上传与沉淀", "课程答疑支持", "智能教案生成与修改"]),
        BoxSpec(1030, 680, 760, 230, "管理员侧需求实体", ["工作流编排与治理", "模型与知识库配置"]),
    ]

    for spec in left_boxes:
        draw_entity_box(draw, spec, title_max=58, title_min=36, body_max=46, body_min=28)
    for spec in right_boxes:
        draw_entity_box(draw, spec, title_max=50, title_min=32, body_max=40, body_min=26)

    diamond_centers = [(820, 255), (820, 535), (820, 815)]
    for cx, cy in diamond_centers:
        draw_diamond(draw, cx=cx, cy=cy, w=200, h=130, text="对应")

    for left, right, (cx, cy) in zip(left_boxes, right_boxes, diamond_centers):
        left_center_y = left.y + left.h // 2
        right_center_y = right.y + right.h // 2
        draw.line((left.x + left.w, left_center_y, cx - 100, cy), fill="black", width=4)
        draw.line((cx + 100, cy, right.x, right_center_y), fill="black", width=4)
        draw_label(draw, 645, cy - 28, "1", size=24)
        draw_label(draw, 935, cy - 28, "N", size=24)

    img.save(path, quality=95)


def generate_ai_core_er(path: Path) -> None:
    width, height = 2000, 1200
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    col1, col2, col3 = 60, 720, 1380
    row1, row2, row3 = 40, 420, 830
    box_w = 560
    box_h = 300

    boxes = {
        "sys_users": BoxSpec(col1, row1, box_w, box_h, "sys_users", ["PK id", "username", "role", "is_active"]),
        "ai_model_apis": BoxSpec(col2, row1, box_w, box_h, "ai_model_apis", ["PK id", "name", "provider", "model_name", "endpoint", "enabled", "is_default"]),
        "ai_workflow_apps": BoxSpec(col3, row1, box_w, box_h, "ai_workflow_apps", ["PK id", "code", "type", "name", "knowledge_base_id", "model_api_id", "owner_user_id", "course_id", "status"]),
        "courses": BoxSpec(col1, row2, box_w, box_h, "courses", ["PK id", "name", "teacher_id", "credit", "capacity", "course_type"]),
        "ai_knowledge_bases": BoxSpec(col2, row2, box_w, box_h, "ai_knowledge_bases", ["PK id", "slug", "name", "owner_type", "owner_user_id", "course_id", "feature"]),
        "ai_lesson_plan_tasks": BoxSpec(col3, row2, box_w, box_h, "ai_lesson_plan_tasks", ["PK id", "teacher_user_id", "course_id", "title", "status", "result", "knowledge_base_id", "model_api_id"]),
        "ai_kb_documents": BoxSpec(col2, row3, box_w, box_h, "ai_kb_documents", ["PK id", "knowledge_base_id", "title", "original_filename", "url", "file_ext", "enabled"]),
        "ai_kb_chunks": BoxSpec(col3, row3, box_w, box_h, "ai_kb_chunks", ["PK id", "knowledge_base_id", "document_id", "seq", "content", "tokens", "document_title"]),
    }

    for name, spec in boxes.items():
        title_max = 44 if len(spec.title) <= 16 else 38
        body_max = 38 if len(spec.lines) <= 5 else 34
        body_min = 24 if name in {"ai_workflow_apps", "ai_lesson_plan_tasks", "ai_kb_documents", "ai_kb_chunks"} else 26
        draw_entity_box(draw, spec, title_max=title_max, title_min=24, body_max=body_max, body_min=body_min)

    sys_users = boxes["sys_users"]
    ai_model_apis = boxes["ai_model_apis"]
    ai_workflow_apps = boxes["ai_workflow_apps"]
    courses = boxes["courses"]
    ai_knowledge_bases = boxes["ai_knowledge_bases"]
    ai_lesson_plan_tasks = boxes["ai_lesson_plan_tasks"]
    ai_kb_documents = boxes["ai_kb_documents"]
    ai_kb_chunks = boxes["ai_kb_chunks"]

    draw_arrow(draw, (sys_users.x + sys_users.w, sys_users.y + sys_users.h // 2), (ai_model_apis.x, ai_model_apis.y + ai_model_apis.h // 2))
    draw_label(draw, 670, 180, "拥有/配置", size=22)

    draw_arrow(draw, (ai_model_apis.x + ai_model_apis.w, ai_model_apis.y + ai_model_apis.h // 2), (ai_workflow_apps.x, ai_workflow_apps.y + ai_workflow_apps.h // 2))
    draw_label(draw, 1320, 180, "模型绑定", size=22)

    draw_arrow(draw, (courses.x + courses.w, courses.y + courses.h // 2), (ai_knowledge_bases.x, ai_knowledge_bases.y + ai_knowledge_bases.h // 2))
    draw_label(draw, 670, 560, "课程关联", size=22)

    draw_arrow(draw, (ai_workflow_apps.x + ai_workflow_apps.w // 2, ai_workflow_apps.y + ai_workflow_apps.h), (ai_lesson_plan_tasks.x + ai_lesson_plan_tasks.w // 2, ai_lesson_plan_tasks.y))
    draw_label(draw, 1660, 392, "任务模型", size=22)

    draw_poly_arrow(
        draw,
        [
            (ai_workflow_apps.x + 90, ai_workflow_apps.y + ai_workflow_apps.h),
            (ai_workflow_apps.x + 90, 390),
            (ai_knowledge_bases.x + ai_knowledge_bases.w // 2, 390),
            (ai_knowledge_bases.x + ai_knowledge_bases.w // 2, ai_knowledge_bases.y),
        ],
    )
    draw_label(draw, 1210, 378, "工作流使用", size=22)

    draw_arrow(draw, (ai_knowledge_bases.x + ai_knowledge_bases.w // 2, ai_knowledge_bases.y + ai_knowledge_bases.h), (ai_kb_documents.x + ai_kb_documents.w // 2, ai_kb_documents.y))
    draw_label(draw, 1000, 790, "知识绑定", size=22)

    draw_arrow(draw, (ai_kb_documents.x + ai_kb_documents.w, ai_kb_documents.y + ai_kb_documents.h // 2), (ai_kb_chunks.x, ai_kb_chunks.y + ai_kb_chunks.h // 2))
    draw_label(draw, 1330, 980, "1:N", size=22)

    img.save(path, quality=95)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    role_path = ASSET_DIR / "fig_2_1_role_demand_er_v2.png"
    ai_path = ASSET_DIR / "fig_3_1_ai_er_compact_v2.png"
    generate_role_er(role_path)
    generate_ai_core_er(ai_path)
    print(role_path)
    print(ai_path)


if __name__ == "__main__":
    main()
