from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..schemas.analysis import AnalysisRequest, WarningResponse, WarningStudent
from ..services.student_analysis import StudentAnalyzer
from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.student import Grade, Student
from ..models.admin_user import StudentUser, ClassRoom

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


@router.get("/student/summary")
async def student_summary(
    grade: str | None = Query(default=None),
    major: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Only teachers or admins can access")

    grade_rows = (await db.execute(select(Grade))).scalars().all()
    if not grade_rows:
        return {"items": []}

    student_ids = sorted({str(g.student_id) for g in grade_rows if g.student_id})
    if not student_ids:
        return {"items": []}

    legacy_students = (await db.execute(select(Student).where(Student.id.in_(student_ids)))).scalars().all()
    legacy_map = {s.id: s for s in legacy_students}

    user_students = (await db.execute(select(StudentUser).where(StudentUser.student_no.in_(student_ids)))).scalars().all()
    user_map = {s.student_no: s for s in user_students}

    class_ids = {s.class_id for s in user_students if s.class_id is not None}
    class_map = {}
    if class_ids:
        classes = (await db.execute(select(ClassRoom).where(ClassRoom.id.in_(class_ids)))).scalars().all()
        class_map = {c.id: c.name for c in classes}

    grade_group: dict[str, dict[int, dict[str, float]]] = {}
    for g in grade_rows:
        sid = str(g.student_id)
        if sid not in student_ids:
            continue
        grade_group.setdefault(sid, {}).setdefault(g.course_id, {})[g.exam_type] = g.score

    def _parse_grade(student_id: str) -> str | None:
        if not student_id:
            return None
        if len(student_id) >= 4 and student_id[:4].isdigit():
            return student_id[:4]
        return None

    items = []
    for sid, course_map in grade_group.items():
        legacy = legacy_map.get(sid)
        user = user_map.get(sid)
        name = (legacy.name if legacy else None) or (user.name if user else None) or sid
        major_name = (legacy.major if legacy else None) or (user.major if user else None) or ""
        grade_value = (legacy.grade if legacy else None) or (str(user.grade_id) if user and user.grade_id else None) or _parse_grade(sid)

        if grade and str(grade_value or "") != str(grade):
            continue
        if major and major_name != major:
            continue

        course_scores = []
        for scores in course_map.values():
            midterm = scores.get("midterm")
            final = scores.get("final")
            if midterm is None and final is None:
                continue
            if midterm is not None and final is not None:
                total = round((midterm + final) / 2 * 0.3 + midterm * 0.3 + final * 0.4, 1)
            else:
                total = midterm if midterm is not None else final
            course_scores.append(total)

        if not course_scores:
            avg_score = 0.0
            failed_courses = 0
        else:
            avg_score = round(sum(course_scores) / len(course_scores), 1)
            failed_courses = sum(1 for s in course_scores if s < 60)

        items.append(
            {
                "student_id": sid,
                "name": name,
                "major": major_name,
                "grade": grade_value,
                "class_id": user.class_id if user else None,
                "class_name": class_map.get(user.class_id) if user else None,
                "avg_score": avg_score,
                "failed_courses": failed_courses,
            }
        )

    return {"items": items}
