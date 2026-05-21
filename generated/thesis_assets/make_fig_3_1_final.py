# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

out = Path(r'D:\bishe\one\generated\thesis_assets')
out.mkdir(parents=True, exist_ok=True)
img_path = out / 'fig_3_1_ai_architecture_code_api_design.png'

W, H = 2600, 980
img = Image.new('RGB', (W, H), 'white')
d = ImageDraw.Draw(img)

font_title = ImageFont.truetype(r'C:\Windows\Fonts\simhei.ttf', 40)
font_col = ImageFont.truetype(r'C:\Windows\Fonts\simhei.ttf', 28)
font_body = ImageFont.truetype(r'C:\Windows\Fonts\simhei.ttf', 24)
font_small = ImageFont.truetype(r'C:\Windows\Fonts\simhei.ttf', 20)

main_title = 'AI模块架构、代码组织与接口关系图'
bbox = d.textbbox((0, 0), main_title, font=font_title)
d.text(((W - (bbox[2] - bbox[0])) / 2, 28), main_title, fill='black', font=font_title)

cols = [
    {
        'title': '角色与场景层',
        'lines': [
            '学生：AI客服、课程问答',
            '教师：课程助手、智能教案',
            '管理员：模型、知识库、工作流配置',
            '先回答“谁来用、从哪进”'
        ]
    },
    {
        'title': '前端页面与代码组织',
        'lines': [
            'AdminAIConfig.vue',
            'CourseAssistant.vue',
            'LessonPlan.vue',
            'StudentAIChat.vue',
            'TeacherAIChat.vue',
            'adminAi.ts / aiPortal.ts / ai.ts'
        ]
    },
    {
        'title': '后端接口层',
        'lines': [
            'admin_ai.py：管理配置接口',
            '/admin/ai/model-apis',
            '/admin/ai/workflows/*',
            '/admin/ai/customer-service/settings',
            'ai_portal.py：场景门户接口',
            '/ai/customer-service/config',
            '/ai/course-assistant/apps',
            '/ai/teacher/kb/upload',
            '/ai/teacher/lesson-plan/tasks',
            'ai_qa.py：/ai_qa/qa/stream'
        ]
    },
    {
        'title': 'AI能力编排层',
        'lines': [
            '工作流确定场景入口',
            '模型优先级选择',
            '文档抽取与规范化',
            '文本分块与知识整理',
            'TF-IDF检索与上下文组装',
            'SSE流式输出',
            '结果回写与状态保留'
        ]
    },
    {
        'title': '数据与资源层',
        'lines': [
            'ai_model_apis',
            'ai_knowledge_bases',
            'ai_kb_documents',
            'ai_kb_chunks',
            'ai_workflow_apps',
            'ai_lesson_plan_tasks',
            'ai_usage_logs'
        ]
    }
]

margin = 60
col_gap = 28
usable_w = W - margin * 2
col_w = (usable_w - col_gap * 4) // 5
box_top = 120
box_h = 650
header_h = 82


def wrap_lines(text, font, max_w):
    lines = []
    cur = ''
    for ch in text:
        test = cur + ch
        if d.textbbox((0, 0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped_text(x, y, text, font, max_w, line_gap=6, align='left'):
    lines = wrap_lines(text, font, max_w)
    yy = y
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=font)
        tw = bb[2] - bb[0]
        tx = x if align == 'left' else x + (max_w - tw) / 2
        d.text((tx, yy), ln, fill='black', font=font)
        yy += (bb[3] - bb[1]) + line_gap
    return yy

for i, col in enumerate(cols):
    x = margin + i * (col_w + col_gap)
    d.rounded_rectangle((x, box_top, x + col_w, box_top + box_h), radius=24, outline='black', width=4)
    d.line((x, box_top + header_h, x + col_w, box_top + header_h), fill='black', width=4)
    title_bb = d.textbbox((0, 0), col['title'], font=font_col)
    d.text((x + (col_w - (title_bb[2] - title_bb[0])) / 2, box_top + 24), col['title'], fill='black', font=font_col)

    y = box_top + header_h + 22
    inner_margin = 18
    max_w = col_w - inner_margin * 2
    for item in col['lines']:
        y = draw_wrapped_text(x + inner_margin, y, '· ' + item, font_body, max_w, line_gap=5, align='left')
        y += 10

arrow_labels = ['场景进入', '页面调用', '接口调度', '数据支撑']
arrow_y = box_top + box_h + 42
for i in range(4):
    x1 = margin + i * (col_w + col_gap) + col_w
    x2 = margin + (i + 1) * (col_w + col_gap)
    d.line((x1 + 8, arrow_y, x2 - 18, arrow_y), fill='black', width=4)
    d.polygon([(x2 - 18, arrow_y), (x2 - 42, arrow_y - 12), (x2 - 42, arrow_y + 12)], fill='black')
    lab = arrow_labels[i]
    bb = d.textbbox((0, 0), lab, font=font_small)
    lx = (x1 + x2 - (bb[2] - bb[0])) / 2
    d.text((lx, arrow_y - 38), lab, fill='black', font=font_small)

note = '说明：这张图把角色入口、前端页面、接口分组、AI能力和底层数据放到同一条设计链上，目的是先把结构关系讲清楚，后面再展开知识组织和数据表设计。'
draw_wrapped_text(110, 905, note, font_small, W - 220, line_gap=6, align='left')

img.save(img_path, quality=95)
print(str(img_path))
