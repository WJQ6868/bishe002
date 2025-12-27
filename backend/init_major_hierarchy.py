import asyncio
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

from sqlalchemy import delete, select

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from app.database import AsyncSessionLocal  # noqa: E402
from app.models.academic import (  # noqa: E402
    AcademicClass,
    AcademicMajor,
    AcademicStudent,
)
from app.models.admin_user import ClassRoom
from app.models.admin_user import StudentUser  # noqa: E402

UNKNOWN_MAJOR_NAME = "\u672a\u8bbe\u7f6e\u4e13\u4e1a"
ACADEMIC_CLASS_CODE_PREFIX = "t_class:"


def normalize_major(raw: str | None) -> str:
    raw = (raw or "").strip()
    if not raw:
        return UNKNOWN_MAJOR_NAME
    return raw


def most_common(values: List[str]) -> str:
    counter: Dict[str, int] = defaultdict(int)
    for value in values:
        counter[value] += 1
    if not counter:
        return UNKNOWN_MAJOR_NAME
    return max(counter.items(), key=lambda kv: kv[1])[0]


async def seed_academic_hierarchy():
    async with AsyncSessionLocal() as session:
        # IMPORTANT: Do NOT delete/recreate AcademicMajor (it is managed by the UI).
        # We only keep academic_students in sync with StudentUser (t_student), and create/update
        # academic_classes mapped from t_class.
        await session.execute(
            delete(AcademicStudent).where(
                ~AcademicStudent.student_code.in_(select(StudentUser.student_no))
            )
        )
        await session.commit()

        result = await session.execute(
            select(StudentUser, ClassRoom)
            .outerjoin(ClassRoom, ClassRoom.id == StudentUser.class_id)
        )
        student_rows: List[Tuple[StudentUser, ClassRoom | None]] = list(result.all())

        if not student_rows:
            raise RuntimeError("t_student 表为空，请先在【学生用户管理】中导入/新增学生")
        # Group students by t_class.id
        class_to_students: Dict[int, List[StudentUser]] = defaultdict(list)
        class_to_room: Dict[int, ClassRoom | None] = {}

        for student, classroom in student_rows:
            class_to_students[int(student.class_id)].append(student)
            if int(student.class_id) not in class_to_room:
                class_to_room[int(student.class_id)] = classroom

        # Determine major name for each class (majority vote among students in the class)
        class_to_major_name: Dict[int, str] = {}
        for class_id, students in class_to_students.items():
            majors = [normalize_major(s.major) for s in students]
            class_to_major_name[class_id] = most_common(majors)

        # Load existing majors (do not delete)
        majors_result = await session.execute(select(AcademicMajor))
        major_by_name: Dict[str, AcademicMajor] = {
            m.name: m for m in majors_result.scalars().all()
        }

        for major_name in sorted(set(class_to_major_name.values())):
            if major_name in major_by_name:
                continue
            major = AcademicMajor(name=major_name)
            session.add(major)
            await session.flush()
            major_by_name[major_name] = major

        # Load existing AcademicClass rows that are mapped from t_class
        existing_class_rows = await session.execute(
            select(AcademicClass).where(
                AcademicClass.code.like(f"{ACADEMIC_CLASS_CODE_PREFIX}%")
            )
        )
        academic_class_by_code: Dict[str, AcademicClass] = {
            c.code: c for c in existing_class_rows.scalars().all() if c.code
        }

        # Upsert classes
        tclass_to_aclass: Dict[int, AcademicClass] = {}
        for t_class_id, students in class_to_students.items():
            major_name = class_to_major_name[t_class_id]
            major = major_by_name[major_name]

            classroom = class_to_room.get(t_class_id)
            class_name = classroom.name if classroom else f"\u73ed\u7ea7{t_class_id}"
            class_code = f"{ACADEMIC_CLASS_CODE_PREFIX}{t_class_id}"

            existing = academic_class_by_code.get(class_code)
            if existing:
                existing.name = class_name
                existing.major_id = major.id
                existing.student_count = len(students)
                tclass_to_aclass[t_class_id] = existing
            else:
                new_class = AcademicClass(
                    major_id=major.id,
                    name=class_name,
                    code=class_code,
                    status=1,
                    student_count=len(students),
                )
                session.add(new_class)
                await session.flush()
                tclass_to_aclass[t_class_id] = new_class

        # Upsert students
        existing_students_result = await session.execute(select(AcademicStudent))
        academic_student_by_code: Dict[str, AcademicStudent] = {
            s.student_code: s for s in existing_students_result.scalars().all()
        }

        for students in class_to_students.values():
            for stu in students:
                student_code = str(stu.student_no)
                target_class = tclass_to_aclass.get(int(stu.class_id))
                if not target_class:
                    continue

                existing_student = academic_student_by_code.get(student_code)
                desired_status = 1 if int(stu.status or 0) == 1 else 0

                if existing_student:
                    existing_student.class_id = target_class.id
                    existing_student.name = stu.name
                    existing_student.gender = int(stu.gender) if stu.gender is not None else None
                    existing_student.mobile = stu.mobile
                    existing_student.status = desired_status
                else:
                    session.add(
                        AcademicStudent(
                            class_id=target_class.id,
                            student_code=student_code,
                            name=stu.name,
                            gender=int(stu.gender) if stu.gender is not None else None,
                            mobile=stu.mobile,
                            status=desired_status,
                        )
                    )

        await session.commit()
        print("Academic classes/students synced from t_student (StudentUser).")


if __name__ == "__main__":
    asyncio.run(seed_academic_hierarchy())
