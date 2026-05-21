from __future__ import annotations

import math
import shutil
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"D:\bishe\one")
DOCX_PATH = Path(r"C:\Users\wangj\Desktop\2405273202-王佳齐-AI赋能的高校教务系统(ai版）.docx")
WORK_DIR = ROOT / "tmp_redraw_fig_3_1_vertical"
ASSET_DIR = ROOT / "generated" / "thesis_assets"
ASSET_PATH = ASSET_DIR / "fig_3_1_ai_module_code_api_vertical.png"
BACKUP_PATH = DOCX_PATH.with_name(DOCX_PATH.stem + "-backup-before-fig3-1-vertical" + DOCX_PATH.suffix)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"


def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates: list[Path] = []
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


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    for ch in text:
        candidate = current + ch
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def fit_font(
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
    max_w = x2 - x1
    max_h = y2 - y1
    for size in range(start_size, min_size - 1, -2):
        font = load_font(size, bold=bold)
        widths = []
        heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            widths.append(bbox[2] - bbox[0])
            heights.append(bbox[3] - bbox[1])
        total_h = sum(heights) + max(0, len(lines) - 1) * line_gap
        if max(widths, default=0) <= max_w and total_h <= max_h:
            return font
    return load_font(min_size, bold=bold)


def draw_centered_lines(
    draw: ImageDraw.ImageDraw,
    box: tuple[float, float, float, float],
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    *,
    line_gap: int = 8,
) -> None:
    x1, y1, x2, y2 = box
    metrics = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        metrics.append((bbox[2] - bbox[0], bbox[3] - bbox[1]))
    total_h = sum(h for _, h in metrics) + max(0, len(lines) - 1) * line_gap
    y = y1 + (y2 - y1 - total_h) / 2
    for (line, (w, h)) in zip(lines, metrics):
        x = x1 + (x2 - x1 - w) / 2
        draw.text((x, y), line, font=font, fill="black")
        y += h + line_gap


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

    title_pad_x = 28
    top_pad = 22
    divider_gap = 18

    title_probe = load_font(title_start, bold=True)
    title_lines = wrap_text(draw, title, title_probe, int((x2 - x1) - title_pad_x * 2))
    title_box = (x1 + title_pad_x, y1 + top_pad, x2 - title_pad_x, y1 + 130)
    title_font = fit_font(
        draw,
        title_lines,
        title_box,
        start_size=title_start,
        min_size=title_min,
        bold=True,
        line_gap=6,
    )
    title_metrics = [draw.textbbox((0, 0), line, font=title_font) for line in title_lines]
    title_h = sum(b[3] - b[1] for b in title_metrics) + max(0, len(title_lines) - 1) * 6
    title_area = (title_box[0], y1 + top_pad, title_box[2], y1 + top_pad + title_h)
    draw_centered_lines(draw, title_area, title_lines, title_font, line_gap=6)

    divider_y = y1 + top_pad + title_h + divider_gap
    draw.line((x1, divider_y, x2, divider_y), fill="black", width=max(3, line_width - 2))

    body_area = (x1 + 28, divider_y + 16, x2 - 28, y2 - 20)
    probe_font = load_font(body_start)
    wrapped_rows: list[str] = []
    for row in rows:
        wrapped_rows.extend(wrap_text(draw, row, probe_font, int(body_area[2] - body_area[0])))
    body_font = fit_font(
        draw,
        wrapped_rows,
        body_area,
        start_size=body_start,
        min_size=body_min,
        bold=False,
        line_gap=8,
    )
    draw_centered_lines(draw, body_area, wrapped_rows, body_font, line_gap=8)


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    width: int = 5,
    head_len: int = 18,
) -> None:
    draw.line([start, end], fill="black", width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    p1 = (end[0] - head_len * math.cos(angle - math.pi / 8), end[1] - head_len * math.sin(angle - math.pi / 8))
    p2 = (end[0] - head_len * math.cos(angle + math.pi / 8), end[1] - head_len * math.sin(angle + math.pi / 8))
    draw.polygon([end, p1, p2], fill="black")


def build_vertical_figure(image_path: Path) -> None:
    width, height = 2480, 3400
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    side = 180
    box_w = width - side * 2
    box_h = 480
    gap = 105
    top = 90

    boxes = []
    for idx in range(5):
        y1 = top + idx * (box_h + gap)
        boxes.append((side, y1, side + box_w, y1 + box_h))

    titles = [
        "角色场景层",
        "前端页面组织",
        "后端接口收口",
        "AI能力编排层",
        "数据与资源层",
    ]
    rows_list = [
        ["学生：AI客服", "学生：课程问答", "教师：资料与教案", "管理员：配置治理"],
        ["StudentAIChat.vue", "AdminAIConfig.vue", "CourseAssistant.vue", "StudentCourseAssistant.vue", "LessonPlan.vue", "aiPortal.ts / ai.ts"],
        ["/admin/ai/*", "/ai/course-assistant/*", "/ai/teacher/*", "/ai_qa/qa/stream", "统一权限校验"],
        ["工作流选择", "模型优先级", "文档抽取分块", "TF-IDF检索组装", "SSE流式输出"],
        ["ai_model_apis", "ai_knowledge_bases", "ai_kb_chunks", "ai_workflow_apps", "ai_lesson_plan_tasks"],
    ]

    for idx, box in enumerate(boxes):
        draw_box(
            draw,
            box,
            titles[idx],
            rows_list[idx],
            title_start=70,
            title_min=56,
            body_start=54,
            body_min=40,
        )

    center_x = width / 2
    for idx in range(4):
        start_y = boxes[idx][3] + 20
        end_y = boxes[idx + 1][1] - 26
        draw_arrow(draw, (center_x, start_y), (center_x, end_y), width=6, head_len=20)

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

    media_path = unzip_dir / "word" / "media" / "image6.png"
    shutil.copy2(png_path, media_path)

    document_xml = unzip_dir / "word" / "document.xml"
    tree = ET.parse(document_xml)
    root = tree.getroot()

    body = root.find(f".//{{{W_NS}}}body")
    if body is None:
        raise RuntimeError("Word body not found.")

    target_caption = "图 3-1 AI模块架构、代码组织与接口关系图"
    target_inline = None
    body_children = list(body)
    for idx, child in enumerate(body_children):
        text = "".join(t.text or "" for t in child.findall(f".//{{{W_NS}}}t"))
        if text.strip() == target_caption:
            for back in range(idx - 1, -1, -1):
                inline = body_children[back].find(f".//{{{WP_NS}}}inline")
                if inline is not None:
                    target_inline = inline
                    break
            break

    if target_inline is None:
        raise RuntimeError("Could not locate figure 3-1 drawing.")

    cx = str(cm_to_emu(14.6))
    cy = str(cm_to_emu(20.4))

    extent = target_inline.find(f"./{{{WP_NS}}}extent")
    if extent is not None:
        extent.set("cx", cx)
        extent.set("cy", cy)

    a_ext = target_inline.find(f".//{{{A_NS}}}xfrm/{{{A_NS}}}ext")
    if a_ext is not None:
        a_ext.set("cx", cx)
        a_ext.set("cy", cy)

    blip_fill = target_inline.find(f".//{{{PIC_NS}}}blipFill")
    if blip_fill is not None:
        src_rect = blip_fill.find(f"./{{{A_NS}}}srcRect")
        if src_rect is not None:
            blip_fill.remove(src_rect)

    doc_pr = target_inline.find(f"./{{{WP_NS}}}docPr")
    if doc_pr is not None:
        doc_pr.set("descr", "fig_3_1_ai_module_code_api_vertical")
    c_nv_pr = target_inline.find(f".//{{{PIC_NS}}}cNvPr")
    if c_nv_pr is not None:
        c_nv_pr.set("descr", "fig_3_1_ai_module_code_api_vertical")

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
    build_vertical_figure(ASSET_PATH)
    update_docx(DOCX_PATH, ASSET_PATH)
    print(f"updated_docx={DOCX_PATH}")
    print(f"backup={BACKUP_PATH}")
    print(f"asset={ASSET_PATH}")


if __name__ == "__main__":
    main()
