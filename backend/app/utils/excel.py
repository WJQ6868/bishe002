import pandas as pd
from typing import List, Dict
from fastapi import UploadFile
import io
from datetime import datetime

class ExcelParser:
    @staticmethod
    async def parse_calendar_events(file: UploadFile) -> List[Dict]:
        """
        解析校历导入 Excel 文件
        支持列: 名称, 类型, 开始时间, 结束时间, 地点, 关联班级, 备注
        """
        content = await file.read()
        try:
            df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise ValueError(f"无法读取 Excel 文件: {str(e)}")
        
        # 检查必要列
        required_columns = ['名称', '类型', '开始时间', '结束时间']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Excel文件缺少必要列: {', '.join(missing_columns)}")
            
        events = []
        for _, row in df.iterrows():
            # 处理日期格式
            try:
                start_date = ExcelParser._format_date(row['开始时间'])
                end_date = ExcelParser._format_date(row['结束时间'])
            except Exception:
                continue # 跳过日期格式错误的行

            events.append({
                "title": str(row['名称']).strip(),
                "type": str(row['类型']).strip(),
                "start_date": start_date,
                "end_date": end_date,
                "location": str(row.get('地点', '')).strip() if pd.notna(row.get('地点')) else "",
                "related_classes": str(row.get('关联班级', '')).strip() if pd.notna(row.get('关联班级')) else "",
                "description": str(row.get('备注', '')).strip() if pd.notna(row.get('备注')) else ""
            })
        return events

    @staticmethod
    def _format_date(date_val) -> str:
        """将各种日期格式转换为 YYYY-MM-DD 字符串"""
        if pd.isna(date_val):
            raise ValueError("日期为空")
        
        if isinstance(date_val, datetime):
            return date_val.strftime('%Y-%m-%d')
        
        date_str = str(date_val).strip()
        # 尝试解析常见格式
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%Y%m%d']:
            try:
                return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # 如果包含时间部分，尝试截取
        if ' ' in date_str:
            return date_str.split(' ')[0]
            
        return date_str
