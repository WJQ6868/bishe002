from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..database import get_db
from ..models.academic import (
    AcademicCollege,
    AcademicClass,
    AcademicClassHeadTeacher,
    AcademicCourse,
    AcademicCourseTeacher,
    AcademicMajor,
    AcademicStudent,
)
from ..models.admin_user import TeacherUser
from ..models.course import Teacher
from ..schemas.academic import (
    CollegeOut,
    ClassOut,
    CourseOut,
    CourseTeacherOut,
    MajorOut,
    StudentOut,
)

router = APIRouter(tags=["Academic Hierarchy"])


class CollegeCreate(BaseModel):
    name: str
    code: str
    status: int = 1


class CollegeUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    status: int | None = None


class MajorCreate(BaseModel):
    name: str
    code: str
    status: int = 1
    college_id: int | None = None


class MajorUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    status: int | None = None
    college_id: int | None = None


class ClassCreate(BaseModel):
    major_id: int
    name: str
    code: str | None = None
    status: int = 1
    # legacy field (kept for backward compatibility); head teacher is managed in a new table
    teacher_id: str | None = None
    student_count: int = 0


class ClassUpdate(BaseModel):
    major_id: int | None = None
    name: str | None = None
    code: str | None = None
    status: int | None = None
    # legacy field (kept for backward compatibility); head teacher is managed in a new table
    teacher_id: str | None = None
    student_count: int | None = None


class StudentCreate(BaseModel):
    class_id: int
    student_code: str
    name: str
    gender: int | None = None
    mobile: str | None = None
    status: int = 1


class StudentUpdate(BaseModel):
    class_id: int | None = None
    student_code: str | None = None
    name: str | None = None
    gender: int | None = None
    mobile: str | None = None
    status: int | None = None


@router.get("/college/list")
async def list_colleges(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AcademicCollege).order_by(AcademicCollege.id))
    colleges = result.scalars().all()
    return {"items": [CollegeOut.model_validate(c) for c in colleges]}


@router.post("/college/add")
async def add_college(payload: CollegeCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(AcademicCollege).where((AcademicCollege.name == payload.name) | (AcademicCollege.code == payload.code)))
    if exists.scalars().first():
        raise HTTPException(status_code=400, detail="学院名称或编码已存在")
    obj = AcademicCollege(name=payload.name, code=payload.code, status=payload.status)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return CollegeOut.model_validate(obj)


@router.put("/college/{college_id}")
async def update_college(college_id: int, payload: CollegeUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AcademicCollege).where(AcademicCollege.id == college_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="学院不存在")
    if payload.name:
        obj.name = payload.name
    if payload.code:
        obj.code = payload.code
    if payload.status is not None:
        obj.status = payload.status
    await db.commit()
    await db.refresh(obj)
    return CollegeOut.model_validate(obj)


@router.delete("/college/{college_id}")
async def delete_college(college_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AcademicCollege).where(AcademicCollege.id == college_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="学院不存在")

    majors_count = await db.execute(
        select(func.count(AcademicMajor.id)).where(AcademicMajor.college_id == college_id)
    )
    if (majors_count.scalar() or 0) > 0:
        raise HTTPException(status_code=400, detail="该学院下存在专业，无法删除")

    await db.delete(obj)
    await db.commit()
    return {"ok": True}


@router.get("/major/list")
async def list_majors(college_id: int | None = Query(default=None), db: AsyncSession = Depends(get_db)):
    query = select(AcademicMajor).order_by(AcademicMajor.id)
    if college_id:
        query = query.where(AcademicMajor.college_id == college_id)
    result = await db.execute(query)
    majors = result.scalars().all()
    return {"items": [MajorOut.model_validate(m) for m in majors]}


@router.post("/major/add")
async def add_major(payload: MajorCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(AcademicMajor).where((AcademicMajor.name == payload.name) | (AcademicMajor.code == payload.code)))
    if exists.scalars().first():
        raise HTTPException(status_code=400, detail="专业名称或编码已存在")
    obj = AcademicMajor(
        name=payload.name,
        code=payload.code,
        status=payload.status,
        college_id=payload.college_id,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return MajorOut.model_validate(obj)


@router.put("/major/{major_id}")
async def update_major(major_id: int, payload: MajorUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AcademicMajor).where(AcademicMajor.id == major_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="专业不存在")
    if payload.name:
        obj.name = payload.name
    if payload.code:
        obj.code = payload.code
    if payload.status is not None:
        obj.status = payload.status
    if payload.college_id is not None:
        obj.college_id = payload.college_id
    await db.commit()
    await db.refresh(obj)
    return MajorOut.model_validate(obj)


@router.delete("/major/{major_id}")
async def delete_major(major_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AcademicMajor).where(AcademicMajor.id == major_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="专业不存在")

    classes_count = await db.execute(
        select(func.count(AcademicClass.id)).where(AcademicClass.major_id == major_id)
    )
    if (classes_count.scalar() or 0) > 0:
        raise HTTPException(status_code=400, detail="该专业下存在班级，无法删除")

    courses_count = await db.execute(
        select(func.count(AcademicCourse.id)).where(AcademicCourse.major_id == major_id)
    )
    if (courses_count.scalar() or 0) > 0:
        raise HTTPException(status_code=400, detail="该专业下存在课程，无法删除")

    await db.delete(obj)
    await db.commit()
    return {"ok": True}


@router.get("/major/class/list")
async def list_classes(
    major_id: int = Query(..., description="Major ID"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AcademicClass)
        .where(AcademicClass.major_id == major_id)
        .order_by(AcademicClass.id)
    )
    classes = result.scalars().all()
    return {"items": [ClassOut.model_validate(c) for c in classes]}


@router.get("/class/list")
async def list_classes_v2(
    college_id: int | None = Query(default=None),
    major_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AcademicClass, AcademicMajor, AcademicClassHeadTeacher, TeacherUser)
        .join(AcademicMajor, AcademicMajor.id == AcademicClass.major_id)
        .join(AcademicClassHeadTeacher, AcademicClassHeadTeacher.class_id == AcademicClass.id, isouter=True)
        .join(TeacherUser, TeacherUser.teacher_no == AcademicClassHeadTeacher.teacher_no, isouter=True)
        .order_by(AcademicClass.id)
    )
    if major_id:
        query = query.where(AcademicClass.major_id == major_id)
    if college_id:
        query = query.where(AcademicMajor.college_id == college_id)
    rows = (await db.execute(query)).all()
    items = []
    for clazz, major, head_link, head_teacher in rows:
        items.append(
            {
                "id": clazz.id,
                "name": clazz.name,
                "code": getattr(clazz, "code", None),
                "status": getattr(clazz, "status", 1),
                "student_count": clazz.student_count,
                "major_id": clazz.major_id,
                "major_name": major.name if major else None,
                "head_teacher_no": head_link.teacher_no if head_link else None,
                "head_teacher_name": head_teacher.name if head_teacher else None,
            }
        )
    return {"items": items}


@router.put("/class/{class_id}/head-teacher")
async def bind_class_head_teacher(class_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    teacher_no = (payload.get("teacher_no") or "").strip()
    res = await db.execute(select(AcademicClass).where(AcademicClass.id == class_id))
    clazz = res.scalars().first()
    if not clazz:
        raise HTTPException(status_code=404, detail="班级不存在")

    existing_res = await db.execute(
        select(AcademicClassHeadTeacher).where(AcademicClassHeadTeacher.class_id == class_id)
    )
    link = existing_res.scalars().first()

    # Unbind
    if not teacher_no:
        if link:
            await db.delete(link)
            await db.commit()
        return {"ok": True, "head_teacher_no": None, "head_teacher_name": None}

    teacher_res = await db.execute(select(TeacherUser).where(TeacherUser.teacher_no == teacher_no))
    teacher = teacher_res.scalars().first()
    if not teacher:
        raise HTTPException(status_code=400, detail="班主任不存在，请先在【教职工用户管理】中新增")

    if link:
        link.teacher_no = teacher_no
    else:
        db.add(AcademicClassHeadTeacher(class_id=class_id, teacher_no=teacher_no))

    await db.commit()
    return {"ok": True, "head_teacher_no": teacher_no, "head_teacher_name": teacher.name}


@router.post("/class/add")
async def add_class(payload: ClassCreate, db: AsyncSession = Depends(get_db)):
    obj = AcademicClass(
        major_id=payload.major_id,
        name=payload.name,
        code=payload.code,
        status=payload.status,
        teacher_id=payload.teacher_id,
        student_count=payload.student_count,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return ClassOut.model_validate(obj)


@router.put("/class/{class_id}")
async def update_class(class_id: int, payload: ClassUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AcademicClass).where(AcademicClass.id == class_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="班级不存在")
    if payload.major_id is not None:
        obj.major_id = payload.major_id
    if payload.name is not None:
        obj.name = payload.name
    if payload.code is not None:
        obj.code = payload.code
    if payload.status is not None:
        obj.status = payload.status
    if payload.teacher_id is not None:
        obj.teacher_id = payload.teacher_id
    if payload.student_count is not None:
        obj.student_count = payload.student_count
    await db.commit()
    await db.refresh(obj)
    return ClassOut.model_validate(obj)


@router.put("/class/{class_id}/teacher")
async def bind_class_teacher(class_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    teacher_id = payload.get("teacher_id")
    if not teacher_id:
        raise HTTPException(status_code=400, detail="缺少 teacher_id")
    res = await db.execute(select(AcademicClass).where(AcademicClass.id == class_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="班级不存在")
    obj.teacher_id = str(teacher_id)
    await db.commit()
    await db.refresh(obj)
    return ClassOut.model_validate(obj)


@router.delete("/class/{class_id}")
async def delete_class(class_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AcademicClass).where(AcademicClass.id == class_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="班级不存在")
    cnt = await db.execute(select(func.count(AcademicStudent.id)).where(AcademicStudent.class_id == class_id))
    if (cnt.scalar() or 0) > 0:
        raise HTTPException(status_code=400, detail="该班级下存在学生，无法删除")
    await db.delete(obj)
    await db.commit()
    return {"ok": True}


@router.get("/class/student/list")
async def list_students(
    class_id: int = Query(..., description="Class ID"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AcademicStudent)
        .where(AcademicStudent.class_id == class_id)
        .order_by(AcademicStudent.id)
    )
    students = result.scalars().all()
    return {"items": [StudentOut.model_validate(s) for s in students]}


@router.get("/student/list")
async def list_students_v2(
    class_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AcademicStudent, AcademicClass)
        .join(AcademicClass, AcademicClass.id == AcademicStudent.class_id)
        .order_by(AcademicStudent.id)
    )
    if class_id:
        query = query.where(AcademicStudent.class_id == class_id)
    rows = (await db.execute(query)).all()
    items = []
    for stu, clazz in rows:
        items.append(
            {
                "id": stu.id,
                "student_code": stu.student_code,
                "name": stu.name,
                "gender": getattr(stu, "gender", None),
                "mobile": getattr(stu, "mobile", None),
                "status": getattr(stu, "status", 1),
                "class_id": stu.class_id,
                "class_name": clazz.name if clazz else None,
            }
        )
    return {"items": items}


@router.get("/student/{student_id}")
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AcademicStudent, AcademicClass).join(AcademicClass, AcademicClass.id == AcademicStudent.class_id).where(AcademicStudent.id == student_id))
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="学生不存在")
    stu, clazz = row
    return {
        "id": stu.id,
        "student_code": stu.student_code,
        "name": stu.name,
        "gender": getattr(stu, "gender", None),
        "mobile": getattr(stu, "mobile", None),
        "status": getattr(stu, "status", 1),
        "class_id": stu.class_id,
        "class_name": clazz.name if clazz else None,
    }


@router.post("/student/add")
async def add_student(payload: StudentCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(AcademicStudent).where(AcademicStudent.student_code == payload.student_code))
    if exists.scalars().first():
        raise HTTPException(status_code=400, detail="学号已存在")
    obj = AcademicStudent(
        class_id=payload.class_id,
        student_code=payload.student_code,
        name=payload.name,
        gender=payload.gender,
        mobile=payload.mobile,
        status=payload.status,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return StudentOut.model_validate(obj)


@router.put("/student/{student_id}")
async def update_student(student_id: int, payload: StudentUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AcademicStudent).where(AcademicStudent.id == student_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="学生不存在")
    if payload.student_code is not None and payload.student_code != obj.student_code:
        exists = await db.execute(select(AcademicStudent).where(AcademicStudent.student_code == payload.student_code))
        if exists.scalars().first():
            raise HTTPException(status_code=400, detail="学号已存在")
        obj.student_code = payload.student_code
    if payload.class_id is not None:
        obj.class_id = payload.class_id
    if payload.name is not None:
        obj.name = payload.name
    if payload.gender is not None:
        obj.gender = payload.gender
    if payload.mobile is not None:
        obj.mobile = payload.mobile
    if payload.status is not None:
        obj.status = payload.status
    await db.commit()
    await db.refresh(obj)
    return StudentOut.model_validate(obj)


@router.delete("/student/{student_id}")
async def delete_student(student_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AcademicStudent).where(AcademicStudent.id == student_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="学生不存在")
    await db.delete(obj)
    await db.commit()
    return {"ok": True}


@router.get("/major/course/list")
async def list_courses(
    major_id: int = Query(..., description="Major ID"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AcademicCourse)
        .where(AcademicCourse.major_id == major_id)
        .order_by(AcademicCourse.id)
    )
    courses = result.scalars().all()
    return {"items": [CourseOut.model_validate(c) for c in courses]}


@router.get("/course/teacher/list")
async def list_course_teachers(
    course_id: int = Query(..., description="Course ID"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AcademicCourseTeacher, Teacher)
        .join(Teacher, Teacher.id == AcademicCourseTeacher.teacher_id, isouter=True)
        .where(AcademicCourseTeacher.course_id == course_id)
    )
    rows = result.all()
    items = []
    for link, teacher in rows:
        name = teacher.name if teacher else f"教师 {link.teacher_id}"
        items.append(CourseTeacherOut(teacher_id=link.teacher_id, name=name))
    return {"items": items}
