from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..schemas.analysis import AnalysisRequest, WarningResponse, WarningStudent
from ..services.student_analysis import StudentAnalyzer
from ..database import get_db

router = APIRouter(prefix="/analysis", tags=["Analysis"])

analyzer = StudentAnalyzer()

@router.post("/student/warning", response_model=WarningResponse)
async def analyze_students(request: AnalysisRequest, db: AsyncSession = Depends(get_db)):
    warning_df, cluster_url, stat_url, report_url = await analyzer.analyze(
        db, 
        request.grade, 
        request.major, 
        use_mock=request.use_mock
    )
    
    warning_list = []
    if not warning_df.empty:
        for _, row in warning_df.iterrows():
            warning_list.append(WarningStudent(
                student_id=row['student_id'],
                name=row['name'],
                avg_score=float(row['avg_score']),
                failed_courses=int(row['failed_courses']),
                warning_reason=row['warning_reason']
            ))
        
    return WarningResponse(
        warning_list=warning_list,
        cluster_plot_url=cluster_url,
        warning_stat_plot_url=stat_url,
        report_download_url=report_url
    )
