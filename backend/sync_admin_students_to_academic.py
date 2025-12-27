import asyncio
from collections import defaultdict

from sqlalchemy import select, func

from app.database import AsyncSessionLocal
from app.models.admin_user import ClassRoom, StudentUser
from app.models.academic import AcademicClass, AcademicStudent


async def sync_students():
    async with AsyncSessionLocal() as session:
        # map t_class.id -> code/name
        cls_rows = (await session.execute(select(ClassRoom))).scalars().all()
        id_to_code = {c.id: c.name for c in cls_rows}

        # map class code -> academic class
        acls_rows = (await session.execute(select(AcademicClass))).scalars().all()
        code_to_acls = {c.code or c.name: c for c in acls_rows}

        # existing academic students map
        existing_codes = {
            s.student_code: s for s in (await session.execute(select(AcademicStudent))).scalars().all()
        }

        inserted = 0
        updated = 0

        stu_rows = (await session.execute(select(StudentUser))).scalars().all()
        for stu in stu_rows:
            class_code = id_to_code.get(stu.class_id)
            acls = code_to_acls.get(class_code)
            if not acls:
                continue
            rec = existing_codes.get(stu.student_no)
            if not rec:
                session.add(
                    AcademicStudent(
                        class_id=acls.id,
                        student_code=stu.student_no,
                        name=stu.name,
                        gender=stu.gender,
                        mobile=stu.parent_mobile or stu.mobile,
                        status=stu.status,
                    )
                )
                inserted += 1
            else:
                changed = False
                if rec.class_id != acls.id:
                    rec.class_id = acls.id
                    changed = True
                if rec.name != stu.name:
                    rec.name = stu.name
                    changed = True
                if rec.gender != stu.gender:
                    rec.gender = stu.gender
                    changed = True
                phone = stu.parent_mobile or stu.mobile
                if phone and rec.mobile != phone:
                    rec.mobile = phone
                    changed = True
                if rec.status != stu.status:
                    rec.status = stu.status
                    changed = True
                if changed:
                    updated += 1

        # update student_count per academic class
        counts = defaultdict(int)
        stu_counts = (
            await session.execute(select(AcademicStudent.class_id, func.count()).group_by(AcademicStudent.class_id))
        ).all()
        for cid, cnt in stu_counts:
            counts[cid] = cnt
        for acls in acls_rows:
            new_cnt = counts.get(acls.id, 0)
            if acls.student_count != new_cnt:
                acls.student_count = new_cnt

        await session.commit()
        print(f"academic_students inserted {inserted}, updated {updated}")


async def main():
    await sync_students()


if __name__ == "__main__":
    asyncio.run(main())