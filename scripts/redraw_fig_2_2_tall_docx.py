from __future__ import annotations

import math
import shutil
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"D:\bishe\one")
DOCX_PATH = Path(r"C:\Users\wangj\Desktop\2405273202-王佳齐-AI赋能的高校教务系统(ai版）.docx")
WORK_DIR = ROOT / "tmp_redraw_fig_2_2_tall"
ASSET_DIR = ROOT / "generated" / "thesis_assets"
ASSET_PATH = ASSET_DIR / "fig_2_2_ai_existing_system_arch_tall.png"
BACKUP_PATH = DOCX_PATH.with_name(DOCX_PATH.stem + "-backup-before-fig2-2-tall" + DOCX_PATH.suffix)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"

NS = {
    "w": W_NS,
    "r": R_NS,
    "a": A_NS,
    "wp": WP_NS,
    "pic": PIC_NS,
}


def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                Path(r"C:\Windows\Fonts\simhei.ttf"),
                Path(r"C:\Windows\Fonts\msyhbd.ttc"),
                Path(r"C:\Windows\Fonts\msyh.ttc"),
            ]
        )
    else:
        candidates.extend(
            [
                Path(r"C:\Windows\Fonts\msyh.ttc"),
                Path(r"C:\Windows\Fonts\simsun.ttc"),
                Path(r"C:\Windows\Fonts\simhei.ttf"),
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> float:
    return draw.textbbox((0, 0), text, font=font)[2]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    if not text:
        return [""]
    line = ""
    result: list[str] = []
    for ch in text:
        candidate = line + ch
        if text_width(draw, candidate, font) <= max_width:
            line = candidate
        else:
            if line:
                result.append(line)
            line = ch
    if line:
        result.append(line)
    return result


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[float, float, float, float],
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    *,
    fill: str = "black",
    line_gap: int = 8,
) -> None:
    x1, y1, x2, y2 = box
    heights = []
    widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + max(0, len(lines) - 1) * line_gap
    current_y = y1 + (y2 - y1 - total_h) / 2
    for idx, line in enumerate(lines):
        w = widths[idx]
        h = heights[idx]
        x = x1 + (x2 - x1 - w) / 2
        y = current_y
        draw.text((x, y), line, font=font, fill=fill)
        current_y += h + line_gap


def fit_font_size(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    box: tuple[float, float, float, float],
    *,
    start_size: int,
    min_size: int,
    bold: bool = False,
    line_gap: int = 8,
) -> ImageFont.FreeTypeFont:
    x1, y1, x2, y2 = box
    box_w = x2 - x1
    box_h = y2 - y1
    for size in range(start_size, min_size - 1, -2):
        font = load_font(size, bold=bold)
        widths = []
        heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            widths.append(bbox[2] - bbox[0])
            heights.append(bbox[3] - bbox[1])
        if widths and max(widths) <= box_w and (sum(heights) + max(0, len(lines) - 1) * line_gap) <= box_h:
            return font
    return load_font(min_size, bold=bold)


def draw_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[float, float, float, float],
    title: str,
    rows: list[str],
    *,
    title_start: int,
    title_min: int,
    body_start: int,
    body_min: int,
    line_width: int = 6,
) -> None:
    x1, y1, x2, y2 = box
    draw.rectangle(box, outline="black", fill="white", width=line_width)

    inner_margin_x = 28
    inner_margin_y = 24
    section_gap = 18
    title_box = (x1 + inner_margin_x, y1 + inner_margin_y, x2 - inner_margin_x, y1 + 110)
    body_box = (x1 + inner_margin_x, y1 + 120, x2 - inner_margin_x, y2 - inner_margin_y)

    title_lines = wrap_text(
        draw,
        title,
        load_font(title_start, bold=True),
        int(title_box[2] - title_box[0]),
    )
    title_font = fit_font_size(
        draw,
        title_lines,
        title_box,
        start_size=title_start,
        min_size=title_min,
        bold=True,
        line_gap=6,
    )
    body_lines: list[str] = []
    probe_font = load_font(body_start, bold=False)
    for row in rows:
        body_lines.extend(wrap_text(draw, row, probe_font, int(body_box[2] - body_box[0])))
    body_font = fit_font_size(
        draw,
        body_lines,
        body_box,
        start_size=body_start,
        min_size=body_min,
        bold=False,
        line_gap=8,
    )

    title_bbox = draw.textbbox((0, 0), "国", font=title_font)
    title_h = title_bbox[3] - title_bbox[1]
    title_block_h = title_h * len(title_lines) + max(0, len(title_lines) - 1) * 6
    title_area = (title_box[0], y1 + 22, title_box[2], y1 + 22 + title_block_h)
    draw_centered_text(draw, title_area, title_lines, title_font, line_gap=6)

    divider_y = y1 + 22 + title_block_h + section_gap
    draw.line((x1, divider_y, x2, divider_y), fill="black", width=max(3, line_width - 2))

    body_area = (body_box[0], divider_y + 16, body_box[2], y2 - 20)
    draw_centered_text(draw, body_area, body_lines, body_font, line_gap=8)


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    width: int = 5,
    head_len: int = 20,
) -> None:
    draw.line([start, end], fill="black", width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    a1 = angle - math.pi / 8
    a2 = angle + math.pi / 8
    p1 = (end[0] - head_len * math.cos(a1), end[1] - head_len * math.sin(a1))
    p2 = (end[0] - head_len * math.cos(a2), end[1] - head_len * math.sin(a2))
    draw.polygon([end, p1, p2], fill="black")


def build_tall_figure(image_path: Path) -> None:
    width, height = 2480, 3400
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    side = 120
    top_gap = 90
    col_gap = 70
    content_w = width - side * 2
    role_w = (content_w - col_gap * 2) / 3

    role_y = top_gap
    role_h = 500
    front_y = 700
    front_h = 300
    backend_y = 1130
    backend_h = 300
    mid_y = 1560
    mid_h = 660
    mid_gap = 100
    mid_w = (content_w - mid_gap) / 2
    data_y = 2370
    data_h = 540

    student = (side, role_y, side + role_w, role_y + role_h)
    teacher = (side + role_w + col_gap, role_y, side + role_w * 2 + col_gap, role_y + role_h)
    admin = (side + (role_w + col_gap) * 2, role_y, side + role_w * 3 + col_gap * 2, role_y + role_h)
    front = (side, front_y, side + content_w, front_y + front_h)
    backend = (side, backend_y, side + content_w, backend_y + backend_h)
    business = (side, mid_y, side + mid_w, mid_y + mid_h)
    ai = (side + mid_w + mid_gap, mid_y, side + mid_w * 2 + mid_gap, mid_y + mid_h)
    data = (side, data_y, side + content_w, data_y + data_h)

    draw_box(
        draw,
        student,
        "学生端",
        ["选课冲突咨询", "成绩查询说明", "请假与报到流程", "AI客服 / 课程助手"],
        title_start=68,
        title_min=56,
        body_start=54,
        body_min=42,
    )
    draw_box(
        draw,
        teacher,
        "教师端",
        ["课程资料整理", "作业与成绩处理", "课程问答沉淀", "智能教案生成"],
        title_start=68,
        title_min=56,
        body_start=54,
        body_min=42,
    )
    draw_box(
        draw,
        admin,
        "管理员端",
        ["用户与流程维护", "模型API配置", "知识库管理", "工作流编排"],
        title_start=68,
        title_min=56,
        body_start=54,
        body_min=42,
    )

    draw_box(
        draw,
        front,
        "前端展示层",
        ["Vue3 + TypeScript + Element Plus", "角色页面 / 业务表单 / AI对话窗口 / SSE流式展示"],
        title_start=74,
        title_min=60,
        body_start=52,
        body_min=38,
    )
    draw_box(
        draw,
        backend,
        "后端服务层",
        ["FastAPI + SQLAlchemy + Socket.IO", "统一接口 / 权限校验 / 业务编排 / AI任务回写"],
        title_start=74,
        title_min=60,
        body_start=52,
        body_min=38,
    )
    draw_box(
        draw,
        business,
        "现有教务业务底座",
        ["课程 / 选课 / 排课", "成绩 / 证书查询", "请假 / 审批流程", "办事大厅 / 报到", "用户 / 角色权限"],
        title_start=66,
        title_min=52,
        body_start=54,
        body_min=42,
    )
    draw_box(
        draw,
        ai,
        "AI增强能力层",
        ["AI客服 / 课程助手", "智能教案任务", "知识库文档分块", "模型API / 工作流", "Prompt组装 / 流式输出"],
        title_start=66,
        title_min=52,
        body_start=54,
        body_min=42,
    )
    draw_box(
        draw,
        data,
        "数据与外部资源层",
        ["SQLite业务数据 / AI配置 / 使用日志 / 知识分块", "DashScope、Ark 等大模型接口", "本地环境与阿里云 Ubuntu 公网部署 wangjiaqi.me"],
        title_start=72,
        title_min=58,
        body_start=52,
        body_min=38,
    )

    role_bottom = role_y + role_h
    for box in (student, teacher, admin):
        cx = (box[0] + box[2]) / 2
        draw_arrow(draw, (cx, role_bottom + 12), (cx, front_y - 28))

    center_x = side + content_w / 2
    draw_arrow(draw, (center_x, front_y + front_h + 12), (center_x, backend_y - 28))

    draw_arrow(
        draw,
        (center_x - 420, backend_y + backend_h + 18),
        ((business[0] + business[2]) / 2, mid_y - 30),
    )
    draw_arrow(
        draw,
        (center_x + 420, backend_y + backend_h + 18),
        ((ai[0] + ai[2]) / 2, mid_y - 30),
    )

    draw_arrow(
        draw,
        ((business[0] + business[2]) / 2 - 120, mid_y + mid_h + 18),
        ((data[0] + data[2]) / 2 - 520, data_y - 28),
    )
    draw_arrow(
        draw,
        ((ai[0] + ai[2]) / 2 + 120, mid_y + mid_h + 18),
        ((data[0] + data[2]) / 2 + 520, data_y - 28),
    )

    image_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(image_path, dpi=(300, 300))


def cm_to_emu(cm: float) -> int:
    return int(round(cm * 360000))


def update_docx(docx_path: Path, png_path: Path) -> None:
    if not BACKUP_PATH.exists():
        shutil.copy2(docx_path, BACKUP_PATH)

    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    unzip_dir = WORK_DIR / "unzipped"
    unzip_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(docx_path, "r") as zf:
        zf.extractall(unzip_dir)

    media_path = unzip_dir / "word" / "media" / "image3.png"
    shutil.copy2(png_path, media_path)

    document_xml = unzip_dir / "word" / "document.xml"
    tree = ET.parse(document_xml)
    root = tree.getroot()

    target_caption = "图 2-2 基于现有教务系统的AI增强总体架构图"
    target_inline = None

    for p in root.findall(f".//{{{W_NS}}}p"):
        text = "".join(t.text or "" for t in p.findall(f".//{{{W_NS}}}t"))
        if text.strip() == target_caption:
            prev = p.getprevious() if hasattr(p, "getprevious") else None
            break

    # xml.etree does not support getprevious, so scan body children directly.
    body = root.find(f".//{{{W_NS}}}body")
    if body is None:
        raise RuntimeError("Word body not found.")

    for idx, child in enumerate(list(body)):
        text = "".join(t.text or "" for t in child.findall(f".//{{{W_NS}}}t"))
        if text.strip() == target_caption:
            for back in range(idx - 1, -1, -1):
                inline = body[back].find(f".//{{{WP_NS}}}inline")
                if inline is not None:
                    target_inline = inline
                    break
            break

    if target_inline is None:
        raise RuntimeError("Could not locate figure 2-2 inline drawing.")

    cx = str(cm_to_emu(14.6))
    cy = str(cm_to_emu(20.0))

    extent = target_inline.find(f"./{{{WP_NS}}}extent")
    if extent is not None:
        extent.set("cx", cx)
        extent.set("cy", cy)

    a_ext = target_inline.find(f".//{{{A_NS}}}xfrm/{{{A_NS}}}ext")
    if a_ext is not None:
        a_ext.set("cx", cx)
        a_ext.set("cy", cy)

    src_rect_parent = target_inline.find(f".//{{{PIC_NS}}}blipFill")
    if src_rect_parent is not None:
        src_rect = src_rect_parent.find(f"./{{{A_NS}}}srcRect")
        if src_rect is not None:
            src_rect_parent.remove(src_rect)

    doc_pr = target_inline.find(f"./{{{WP_NS}}}docPr")
    if doc_pr is not None:
        doc_pr.set("descr", "fig_2_2_ai_existing_system_arch_tall")

    c_nv_pr = target_inline.find(f".//{{{PIC_NS}}}cNvPr")
    if c_nv_pr is not None:
        c_nv_pr.set("descr", "fig_2_2_ai_existing_system_arch_tall")

    ET.register_namespace("w", W_NS)
    ET.register_namespace("r", R_NS)
    ET.register_namespace("a", A_NS)
    ET.register_namespace("wp", WP_NS)
    ET.register_namespace("pic", PIC_NS)
    tree.write(document_xml, encoding="utf-8", xml_declaration=True)

    tmp_docx = WORK_DIR / "updated.docx"
    with zipfile.ZipFile(tmp_docx, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in unzip_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(unzip_dir))

    shutil.copy2(tmp_docx, docx_path)


def main() -> None:
    build_tall_figure(ASSET_PATH)
    update_docx(DOCX_PATH, ASSET_PATH)
    print(f"updated_docx={DOCX_PATH}")
    print(f"backup={BACKUP_PATH}")
    print(f"asset={ASSET_PATH}")


if __name__ == "__main__":
    main()
