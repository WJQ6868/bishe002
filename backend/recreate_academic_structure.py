import asyncio

from sqlalchemy import select

from app.database import Base, engine, AsyncSessionLocal
from app.models.academic import AcademicCollege, AcademicMajor

# 学院与专业基础数据
college_seed = {"name": "信息工程学院", "code": "C01", "status": 1}
major_seed = {
    "计算机网络技术": "01",
    "软件工程": "02",
    "网络安全": "03",
    "人工智能": "04",
    "大数据": "05",
    "工业互联网": "06",
}


async def ensure_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_college_major() -> None:
    async with AsyncSessionLocal() as session:
        # upsert college
        res = await session.execute(select(AcademicCollege).where(AcademicCollege.code == college_seed["code"]))
        college = res.scalars().first()
        if not college:
            college = AcademicCollege(**college_seed)
            session.add(college)
            await session.flush()
        else:
            college.name = college_seed["name"]
            college.status = college_seed["status"]

        # upsert majors under the college
        for name, code in major_seed.items():
            res = await session.execute(select(AcademicMajor).where(AcademicMajor.code == code))
            major = res.scalars().first()
            if not major:
                major = AcademicMajor(name=name, code=code, status=1, college_id=college.id)
                session.add(major)
            else:
                major.name = name
                major.status = 1
                major.college_id = college.id

        await session.commit()


async def main() -> None:
    await ensure_tables()
    await seed_college_major()
    # 复用已有的班级/学生脚本，填充 academic_classes 与 academic_students
    from seed_academic_classes_students import main as seed_classes_students

    await seed_classes_students()


if __name__ == "__main__":
    asyncio.run(main())