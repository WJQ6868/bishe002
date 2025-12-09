import asyncio
import sys
import os
import json

# Add backend to path
sys.path.append(os.getcwd())

from app.database import engine, Base, AsyncSessionLocal
from app.models.service import ServiceItem
from app.models.user import User

async def init_service_data():
    print("Initializing service hall data...")
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        # Check if data exists
        from sqlalchemy import select
        result = await session.execute(select(ServiceItem))
        if result.scalars().first():
            print("Service data already exists.")
            return

        # Default Service Items
        items = [
            {
                "name": "学籍异动申请",
                "category": "学籍管理",
                "icon": "User",
                "processing_time": "3个工作日",
                "guide": "<p>适用于学生因病、因事等原因需要办理休学、复学、退学等学籍变动的情况。</p>",
                "apply_conditions": "<p>1. 符合学校学籍管理规定；<br>2. 提供相关证明材料。</p>",
                "required_materials": json.dumps([{"name": "申请书", "type": "file"}, {"name": "证明材料", "type": "file"}], ensure_ascii=False),
                "process": json.dumps([{"node": "提交申请", "desc": "学生在线填写"}, {"node": "院系审核", "desc": "辅导员/书记审核"}, {"node": "教务处审批", "desc": "教务处最终确认"}], ensure_ascii=False),
                "apply_fields": json.dumps([
                    {"name": "异动类型", "type": "select", "options": ["休学", "复学", "退学"], "required": True},
                    {"name": "申请原因", "type": "textarea", "required": True}
                ], ensure_ascii=False)
            },
            {
                "name": "成绩复核申请",
                "category": "成绩管理",
                "icon": "DataLine",
                "processing_time": "5个工作日",
                "guide": "<p>学生对期末考试成绩有异议，可在规定时间内申请复核。</p>",
                "apply_conditions": "<p>1. 成绩公布后3个工作日内；<br>2. 仅复核统分错误，不重新评阅。</p>",
                "required_materials": json.dumps([], ensure_ascii=False),
                "process": json.dumps([{"node": "提交申请", "desc": "学生在线填写"}, {"node": "开课学院复核", "desc": "教学秘书核查试卷"}], ensure_ascii=False),
                "apply_fields": json.dumps([
                    {"name": "课程名称", "type": "input", "required": True},
                    {"name": "原成绩", "type": "input", "required": True},
                    {"name": "复核理由", "type": "textarea", "required": True}
                ], ensure_ascii=False)
            },
            {
                "name": "调课申请",
                "category": "课程管理",
                "icon": "Calendar",
                "processing_time": "1个工作日",
                "guide": "<p>教师因公出差、生病等原因需要调整上课时间。</p>",
                "apply_conditions": "<p>提前1天申请。</p>",
                "required_materials": json.dumps([], ensure_ascii=False),
                "process": json.dumps([{"node": "提交申请", "desc": "教师填写"}, {"node": "教务处审批", "desc": "审核时间冲突"}], ensure_ascii=False),
                "apply_fields": json.dumps([
                    {"name": "原课程时间", "type": "datetime", "required": True},
                    {"name": "拟调整时间", "type": "datetime", "required": True},
                    {"name": "调课原因", "type": "textarea", "required": True}
                ], ensure_ascii=False)
            },
            {
                "name": "在读证明办理",
                "category": "证书办理",
                "icon": "Document",
                "processing_time": "即时办理",
                "guide": "<p>申请电子版在读证明。</p>",
                "apply_conditions": "<p>在校注册学生。</p>",
                "required_materials": json.dumps([], ensure_ascii=False),
                "process": json.dumps([{"node": "提交申请", "desc": "系统自动生成"}], ensure_ascii=False),
                "apply_fields": json.dumps([
                    {"name": "用途", "type": "input", "required": True}
                ], ensure_ascii=False)
            },
             {
                "name": "教室借用申请",
                "category": "其他服务",
                "icon": "School",
                "processing_time": "2个工作日",
                "guide": "<p>学生社团活动借用教室。</p>",
                "apply_conditions": "<p>需指导老师批准。</p>",
                "required_materials": json.dumps([{"name": "活动策划书", "type": "file"}], ensure_ascii=False),
                "process": json.dumps([{"node": "提交申请", "desc": "填写活动信息"}, {"node": "审批", "desc": "管理员审核"}], ensure_ascii=False),
                "apply_fields": json.dumps([
                    {"name": "借用时间", "type": "datetime", "required": True},
                    {"name": "借用教室", "type": "input", "required": True},
                    {"name": "活动人数", "type": "number", "required": True}
                ], ensure_ascii=False)
            }
        ]

        for item_data in items:
            item = ServiceItem(**item_data)
            session.add(item)
        
        await session.commit()
        print("Service data initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_service_data())
