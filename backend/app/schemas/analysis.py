from pydantic import BaseModel, Field
from typing import List, Optional

class AnalysisRequest(BaseModel):
    grade: Optional[str] = Field(None, description="年级")
    major: Optional[str] = Field(None, description="专业")
    use_mock: Optional[bool] = Field(True, description="是否使用模拟数据")

class WarningStudent(BaseModel):
    student_id: str
    name: str
    avg_score: float
    failed_courses: int
    warning_reason: str

class WarningResponse(BaseModel):
    warning_list: List[WarningStudent]
    cluster_plot_url: str
    warning_stat_plot_url: str
    report_download_url: str
