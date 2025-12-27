import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.academic import AcademicMajor, AcademicClass, AcademicStudent
from app.models.admin_user import ClassRoom, StudentUser

major_code_map = {
    '计算机网络技术': '01',
    '软件工程': '02',
    '网络安全': '03',
    '人工智能': '04',
    '大数据': '05',
    '工业互联网': '06',
}

class_plan = {k: ['01', '02'] for k in major_code_map}
grade_year = 2024

async def main():
    async with AsyncSessionLocal() as session:
        majors_res = await session.execute(select(AcademicMajor))
        majors = {m.name: m for m in majors_res.scalars().all()}
        class_refs = []
        for major_name, seq_list in class_plan.items():
            major_obj = majors.get(major_name)
            if not major_obj:
                print(f"[WARN] major not found: {major_name}, skip")
                continue
            major_code = major_code_map[major_name]
            for seq in seq_list:
                class_code = f"24{major_code}{seq}"
                room_res = await session.execute(select(ClassRoom).where(ClassRoom.name == class_code))
                room = room_res.scalars().first()
                if not room:
                    room = ClassRoom(name=class_code, grade_id=grade_year, head_teacher_id=None)
                    session.add(room)
                    await session.flush()
                acls_res = await session.execute(select(AcademicClass).where(AcademicClass.code == class_code))
                acls = acls_res.scalars().first()
                if not acls:
                    acls = AcademicClass(
                        major_id=major_obj.id,
                        name=class_code,
                        code=class_code,
                        status=1,
                        student_count=0,
                    )
                    session.add(acls)
                    await session.flush()
                else:
                    acls.major_id = major_obj.id
                    acls.name = class_code
                    acls.code = class_code
                    acls.status = 1
                class_refs.append((class_code, major_name, acls, room))
        await session.flush()

        for class_code, major_name, acls, room in class_refs:
            major_code = major_code_map[major_name]
            seq = class_code[-2:]
            for i in range(1, 11):
                student_no = f"24{major_code}{seq}{i:02d}"
                name = f"学生{seq}{i:02d}"
                mobile = f"1380000{major_code}{seq}{i:02d}"[-11:]
                su_res = await session.execute(select(StudentUser).where(StudentUser.student_no == student_no))
                su = su_res.scalars().first()
                if not su:
                    su = StudentUser(
                        student_no=student_no,
                        name=name,
                        gender=1 if i % 2 else 2,
                        parent_mobile=mobile,
                        grade_id=grade_year,
                        class_id=room.id,
                        major=major_name,
                        student_status=1,
                        status=1,
                    )
                    session.add(su)
                else:
                    su.name = name
                    su.gender = 1 if i % 2 else 2
                    su.parent_mobile = su.parent_mobile or mobile
                    su.grade_id = grade_year
                    su.class_id = room.id
                    su.major = major_name
                    su.student_status = 1
                    su.status = 1
                astu_res = await session.execute(select(AcademicStudent).where(AcademicStudent.student_code == student_no))
                astu = astu_res.scalars().first()
                if not astu:
                    astu = AcademicStudent(
                        class_id=acls.id,
                        student_code=student_no,
                        name=name,
                        gender=1 if i % 2 else 2,
                        mobile=mobile,
                        status=1,
                    )
                    session.add(astu)
                else:
                    astu.class_id = acls.id
                    astu.name = name
                    astu.gender = 1 if i % 2 else 2
                    astu.mobile = astu.mobile or mobile
                    astu.status = 1
            acls.student_count = 10

        await session.commit()
        print("done")

if __name__ == "__main__":
    asyncio.run(main())
