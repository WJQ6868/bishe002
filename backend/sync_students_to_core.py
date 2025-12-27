import asyncio
from typing import Iterable

from sqlalchemy import select, text

from app.database import AsyncSessionLocal, engine
from app.dependencies.auth import get_password_hash
from app.models.admin_user import StudentUser
from app.models.student import Student
from app.models.user import User, UserProfile


async def _sync_students() -> None:
    async with AsyncSessionLocal() as session:
        stu_rows: Iterable[StudentUser] = (
            await session.execute(select(StudentUser))
        ).scalars().all()

        created_users = 0
        updated_users = 0
        created_profiles = 0
        updated_profiles = 0
        created_legacy = 0
        updated_legacy = 0

        for stu in stu_rows:
            username = stu.student_no

            user = (
                await session.execute(select(User).where(User.username == username))
            ).scalars().first()
            if not user:
                user = User(
                    username=username,
                    password=get_password_hash("123456"),
                    role="student",
                    is_active=stu.status == 1,
                )
                session.add(user)
                await session.flush()
                created_users += 1
            else:
                changed = False
                if user.role != "student":
                    user.role = "student"
                    changed = True
                is_active = stu.status == 1
                if user.is_active != is_active:
                    user.is_active = is_active
                    changed = True
                if changed:
                    updated_users += 1

            profile = (
                await session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
            ).scalars().first()
            grade = str(stu.grade_id) if stu.grade_id is not None else None
            if not profile:
                profile = UserProfile(user_id=user.id, name=stu.name, grade=grade)
                session.add(profile)
                created_profiles += 1
            else:
                changed = False
                if profile.name != stu.name:
                    profile.name = stu.name
                    changed = True
                if profile.grade != grade:
                    profile.grade = grade
                    changed = True
                if changed:
                    updated_profiles += 1

            legacy = (
                await session.execute(select(Student).where(Student.id == username))
            ).scalars().first()
            if not legacy:
                session.add(
                    Student(
                        id=username,
                        name=stu.name,
                        major=stu.major,
                        grade=grade,
                    )
                )
                created_legacy += 1
            else:
                changed = False
                if legacy.name != stu.name:
                    legacy.name = stu.name
                    changed = True
                if legacy.major != stu.major:
                    legacy.major = stu.major
                    changed = True
                if legacy.grade != grade:
                    legacy.grade = grade
                    changed = True
                if changed:
                    updated_legacy += 1

        await session.commit()

        print(
            f"users: +{created_users}, updated {updated_users}; "
            f"profiles: +{created_profiles}, updated {updated_profiles}; "
            f"students: +{created_legacy}, updated {updated_legacy}"
        )


async def _drop_academic_tables() -> None:
    drop_list = [
        "academic_course_teachers",
        "academic_courses",
        "academic_students",
        "academic_class_head_teachers",
        "academic_classes",
        "academic_majors",
        "academic_colleges",
    ]
    async with engine.begin() as conn:
        for tbl in drop_list:
            await conn.execute(text(f"DROP TABLE IF EXISTS {tbl}"))
    print("dropped academic_* tables (if they existed)")


async def main() -> None:
    await _sync_students()
    await _drop_academic_tables()


if __name__ == "__main__":
    asyncio.run(main())