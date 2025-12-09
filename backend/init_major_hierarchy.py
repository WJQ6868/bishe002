import asyncio
import os
import random
import sys
from collections import defaultdict
from itertools import cycle
from typing import Iterable, List

from sqlalchemy import delete, select

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from app.database import AsyncSessionLocal  # noqa: E402
from app.models.academic import (  # noqa: E402
    AcademicClass,
    AcademicCourse,
    AcademicCourseTeacher,
    AcademicMajor,
    AcademicStudent,
)
from app.models.course import Course as LegacyCourse, Teacher  # noqa: E402
from app.models.student import Student as LegacyStudent  # noqa: E402

TARGET_MAJORS = [
    "\u8ba1\u7b97\u673a",  # 计算机
    "\u8f6f\u4ef6\u5de5\u7a0b",  # 软件工程
    "\u7f51\u7edc\u5b89\u5168",  # 网络安全
    "\u4eba\u5de5\u667a\u80fd",  # 人工智能
    "\u5927\u6570\u636e",  # 大数据
    "\u5de5\u4e1a\u4e92\u8054\u7f51",  # 工业互联网
]
MAJOR_NAME_MAP = {
    "Computer Science": TARGET_MAJORS[0],
    "Software Engineering": TARGET_MAJORS[1],
    TARGET_MAJORS[5]: TARGET_MAJORS[5],
}
FALLBACK_MAJORS = cycle(TARGET_MAJORS)

CLASS_SIZE_RANGE = (28, 40)
MIN_CLASS_SIZE = 20
COURSE_COUNT_RANGE = (8, 12)
TEACHER_COUNT_RANGE = (1, 3)


def normalize_major(raw: str | None) -> str:
    raw = (raw or "").strip()
    if not raw:
        return next(FALLBACK_MAJORS)
    if raw in MAJOR_NAME_MAP:
        return MAJOR_NAME_MAP[raw]
    if raw in TARGET_MAJORS:
        return raw
    return next(FALLBACK_MAJORS)


def iter_class_chunks(students: List[LegacyStudent]) -> Iterable[list[LegacyStudent]]:
    if not students:
        return
    chunk_size = random.randint(*CLASS_SIZE_RANGE)
    chunks = [
        students[i : i + chunk_size]
        for i in range(0, len(students), chunk_size)
    ]
    if len(chunks) > 1 and len(chunks[-1]) < MIN_CLASS_SIZE:
        chunks[-2].extend(chunks[-1])
        chunks.pop()

    for chunk in chunks:
        yield chunk


async def seed_academic_hierarchy():
    async with AsyncSessionLocal() as session:
        for model in [
            AcademicCourseTeacher,
            AcademicStudent,
            AcademicCourse,
            AcademicClass,
            AcademicMajor,
        ]:
            await session.execute(delete(model))
        await session.commit()

        students_result = await session.execute(select(LegacyStudent))
        students = students_result.scalars().all()
        courses_result = await session.execute(select(LegacyCourse))
        courses = courses_result.scalars().all()
        teacher_rows = await session.execute(select(Teacher))
        teacher_ids = [str(t.id) for t in teacher_rows.scalars().all()]

        if not students:
            raise RuntimeError("students 表为空，请先导入学生数据")
        if not courses:
            raise RuntimeError("courses 表为空，请先导入课程数据")

        students_sorted = sorted(students, key=lambda s: (s.grade or "", s.id))
        major_students: dict[str, list[LegacyStudent]] = defaultdict(list)
        for stu in students_sorted:
            major_students[normalize_major(stu.major)].append(stu)

        major_records: dict[str, AcademicMajor] = {}
        for major_name in TARGET_MAJORS:
            major = AcademicMajor(name=major_name)
            session.add(major)
            await session.flush()
            major_records[major_name] = major

            grouped_by_grade: dict[str, list[LegacyStudent]] = defaultdict(list)
            for stu in major_students.get(major_name, []):
                grouped_by_grade[(stu.grade or "").strip()].append(stu)

            class_index = 1
            grade_keys = sorted(key for key in grouped_by_grade.keys() if key) or [""]
            if "" in grouped_by_grade and "" not in grade_keys:
                grade_keys.append("")

            for grade_key in grade_keys:
                grade_students = grouped_by_grade.get(grade_key, [])
                grade_students.sort(key=lambda s: s.id)
                for chunk in iter_class_chunks(grade_students):
                    suffix = "\u73ed"
                    if grade_key:
                        class_name = f"{major_name}{grade_key}{class_index}{suffix}"
                    else:
                        class_name = f"{major_name}{class_index}{suffix}"

                    clazz = AcademicClass(
                        major_id=major.id,
                        name=class_name,
                        student_count=len(chunk),
                    )
                    session.add(clazz)
                    await session.flush()

                    for stu in chunk:
                        session.add(
                            AcademicStudent(
                                class_id=clazz.id,
                                student_code=stu.id,
                                name=stu.name,
                            )
                        )
                    class_index += 1

        for major in major_records.values():
            if courses:
                desired = random.randint(*COURSE_COUNT_RANGE)
                count = min(len(courses), desired)
                selected_courses = random.sample(courses, count)
            else:
                selected_courses = []

            for course in selected_courses:
                credit = float(course.credit or 3)
                class_hours = getattr(course, "class_hours", None)
                if not class_hours:
                    class_hours = int(max(credit, 2) * 16)

                ac_course = AcademicCourse(
                    major_id=major.id,
                    name=course.name,
                    credit=credit,
                    class_hours=class_hours,
                )
                session.add(ac_course)
                await session.flush()

                linked_teacher_ids: list[str] = []
                if course.teacher_id:
                    linked_teacher_ids.append(str(course.teacher_id))
                extra_needed = max(TEACHER_COUNT_RANGE[0], random.randint(*TEACHER_COUNT_RANGE)) - len(linked_teacher_ids)
                pool = [tid for tid in teacher_ids if tid not in linked_teacher_ids]
                random.shuffle(pool)
                linked_teacher_ids.extend(pool[: max(0, extra_needed)])

                for teacher_id in linked_teacher_ids:
                    session.add(
                        AcademicCourseTeacher(
                            course_id=ac_course.id,
                            teacher_id=teacher_id,
                        )
                    )

        await session.commit()
        print("Academic hierarchy data synced from real tables.")


if __name__ == "__main__":
    asyncio.run(seed_academic_hierarchy())
