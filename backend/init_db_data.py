import asyncio
import sys
import os
import random
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.database import engine, AsyncSessionLocal, Base
from app.models.student import Student, StudentWarning, CourseSelection, Grade
from app.models.course import Course, Teacher
from app.models.user import User
from app.models.schedule import Classroom, Schedule, ClassroomResource
from app.models.leave import LeaveApply
from app.models.teaching import Attendance, Homework, HomeworkSubmit, ClassAdjust, WorkSchedule
from app.dependencies.auth import get_password_hash
from datetime import datetime, timedelta


DEMO_STUDENT_ID = "20230001"


async def ensure_demo_student_data(session: AsyncSession):
    """Ensure demo student (20230001) has persistent course selections and grades.

    This is intentionally idempotent so it can run on existing databases.
    """
    # 1) Ensure student row exists
    result = await session.execute(select(Student).where(Student.id == DEMO_STUDENT_ID))
    student = result.scalars().first()
    if not student:
        student = Student(
            id=DEMO_STUDENT_ID,
            name="学生20230001",
            major="计算机科学",
            grade="2023",
        )
        session.add(student)
        await session.commit()
    else:
        # Keep enrollment year consistent
        if getattr(student, "grade", None) != "2023":
            student.grade = "2023"
            await session.commit()

    # 2) Ensure there are courses to bind
    c_res = await session.execute(select(Course).order_by(Course.id))
    all_courses = c_res.scalars().all()
    if not all_courses:
        return

    # Prefer a stable subset
    selected_courses = all_courses[:5] if len(all_courses) >= 5 else all_courses

    # 3) Ensure course selections
    sel_res = await session.execute(
        select(CourseSelection.course_id).where(CourseSelection.student_id == DEMO_STUDENT_ID)
    )
    existing_course_ids = {row[0] for row in sel_res.all()}
    for course in selected_courses:
        if course.id in existing_course_ids:
            continue
        session.add(
            CourseSelection(
                student_id=DEMO_STUDENT_ID,
                course_id=course.id,
                absent_count=0,
                submit_homework_rate=1.0,
            )
        )
    await session.commit()

    # 4) Ensure grades (history成绩) for a few courses
    grade_res = await session.execute(
        select(Grade.course_id).where(Grade.student_id == DEMO_STUDENT_ID)
    )
    existing_grade_course_ids = {row[0] for row in grade_res.all()}
    grade_targets = selected_courses[:4] if len(selected_courses) >= 4 else selected_courses
    for idx, course in enumerate(grade_targets):
        if course.id not in existing_grade_course_ids:
            # Make scores look realistic
            score = [92, 85, 78, 88][idx] if idx < 4 else random.randint(70, 95)
            session.add(
                Grade(
                    student_id=DEMO_STUDENT_ID,
                    course_id=course.id,
                    score=score,
                    exam_type="final",
                )
            )

        # Make semester distribution more believable for grade pages.
        # Only adjust if create_time looks like "freshly initialized".
        try:
            if getattr(course, "create_time", None) and getattr(course.create_time, "year", 9999) >= 2025:
                course.create_time = [
                    datetime(2023, 10, 1),
                    datetime(2024, 3, 1),
                    datetime(2024, 10, 1),
                    datetime(2025, 3, 1),
                ][min(idx, 3)]
        except Exception:
            pass

    await session.commit()

# Mock Data
MAJORS = ["计算机科学", "软件工程", "人工智能", "数据科学"]
COURSE_NAMES = [
    "Python程序设计", "数据结构", "算法分析", "数据库系统", 
    "操作系统", "计算机网络", "人工智能导论", "机器学习", 
    "Web开发技术", "软件工程导论"
]
TEACHER_NAMES = ["张教授", "李老师", "王博士", "赵讲师", "刘教授"]
STUDENT_NAMES_PREFIX = ["赵", "钱", "孙", "李", "周", "吴", "郑", "王"]
STUDENT_NAMES_SUFFIX = ["伟", "芳", "娜", "敏", "静", "强", "磊", "洋", "艳", "杰"]
CLASSROOM_NAMES = ["A101", "A102", "A201", "A202", "B101", "B102", "C301", "C302"]
DAYS = ["周一", "周二", "周三", "周四", "周五"]
PERIODS = ["第1-2节", "第3-4节", "第5-6节", "第7-8节"]

async def init_data():
    async with AsyncSessionLocal() as session:
        print("Starting data initialization...")

        # 0. Create System Users
        users = [
            {"username": "admin", "password": "admin", "role": "admin"},
            {"username": "teacher", "password": "teacher", "role": "teacher"},
            {"username": "student", "password": "student", "role": "student"},
            # Specific test accounts
            {"username": "800001", "password": "123456", "role": "admin"},
            {"username": "100001", "password": "123456", "role": "teacher"},
            {"username": "2023001", "password": "123456", "role": "student"},
            {"username": "20230001", "password": "123456", "role": "student"},
        ]
        
        for user_data in users:
            hashed_password = get_password_hash(user_data["password"])
            # Check if user exists
            result = await session.execute(select(User).where(User.username == user_data["username"]))
            existing_user = result.scalars().first()
            if existing_user:
                existing_user.password = hashed_password
            else:
                user = User(
                    username=user_data["username"],
                    password=hashed_password,
                    role=user_data["role"]
                )
                session.add(user)
        await session.commit()
        print(f"Created/Updated {len(users)} system users with hashed passwords.")

        # Check if data already exists
        result = await session.execute(select(Teacher))
        existing_teachers = result.scalars().all()
        if existing_teachers:
            print(f"Data already exists ({len(existing_teachers)} teachers found).")
            
            # Still check and populate classrooms and schedules if they're empty
            result_classrooms = await session.execute(select(Classroom))
            existing_classrooms = result_classrooms.scalars().all()
            
            if not existing_classrooms:
                print("Generating classrooms and schedules...")
                await generate_classrooms_and_schedules(session, existing_teachers)
            else:
                print("All data complete. Skipping generation.")

            # Ensure demo student data even when DB already initialized.
            await ensure_demo_student_data(session)
            return

        # 1. Create Teachers
        teachers = []
        for i, name in enumerate(TEACHER_NAMES):
            teacher_id = f"T{100001 + i}"  # 教师工号: T100001, T100002, ...
            teacher = Teacher(
                id=teacher_id,
                name=name,
                password="123456",
                dept="计算机学院",
                phone=f"138{i:08d}"
            )
            session.add(teacher)
            teachers.append(teacher)
            
            # 同步创建 sys_users 记录
            result = await session.execute(select(User).where(User.username == teacher_id))
            if not result.scalars().first():
                sys_user = User(username=teacher_id, password="123456", role="teacher")
                session.add(sys_user)
        
        await session.commit()
        print(f"Created {len(teachers)} teachers.")

        # 2. Create Courses
        courses = []
        for i, name in enumerate(COURSE_NAMES):
            teacher = teachers[i % len(teachers)]
            course = Course(
                name=name,
                credit=random.choice([2, 3, 4]),
                teacher_id=teacher.id,  # 使用教师工号
                capacity=50,
                course_type=random.choice(["必修", "选修"]),
            )
            session.add(course)
            courses.append(course)
        await session.commit()
        print(f"Created {len(courses)} courses.")

        # 3. Create Classrooms
        classrooms = []
        for name in CLASSROOM_NAMES:
            classroom = Classroom(
                name=name,
                capacity=random.choice([30, 40, 50, 60]),
                is_multimedia=random.choice([True, False])
            )
            session.add(classroom)
            await session.flush()
            resource = ClassroomResource(
                classroom_id=classroom.id,
                code=f"CLS-{classroom.id:04d}",
                location=f"{name[0]}栋{name}",
                devices=json.dumps(["多媒体"]) if classroom.is_multimedia else None,
                status="idle",
            )
            session.add(resource)
            classrooms.append(classroom)
        await session.commit()
        print(f"Created {len(classrooms)} classrooms.")

        # 4. Create Schedules
        schedules = []
        used_slots = set()  # Track (classroom_id, day, period) and (teacher_id, day, period)
        
        for course in courses:
            # Each course gets 2 time slots per week
            slots_assigned = 0
            attempts = 0
            max_attempts = 50
            
            while slots_assigned < 2 and attempts < max_attempts:
                attempts += 1
                day = random.randint(0, 4)  # 0-4 for Mon-Fri
                period = random.randint(0, 3)  # 0-3 for periods
                classroom = random.choice(classrooms)
                
                # Check conflicts
                classroom_slot = (classroom.id, day, period)
                teacher_slot = (course.teacher_id, day, period)
                
                if classroom_slot not in used_slots and teacher_slot not in used_slots:
                    schedule = Schedule(
                        course_id=course.id,
                        classroom_id=classroom.id,
                        teacher_id=course.teacher_id,
                        day=day,
                        period=period
                    )
                    session.add(schedule)
                    schedules.append(schedule)
                    used_slots.add(classroom_slot)
                    used_slots.add(teacher_slot)
                    slots_assigned += 1
        
        await session.commit()
        print(f"Created {len(schedules)} schedule entries.")

        # 5. Create Admins
        admins = []
        admin_names = ["系统管理员", "教务管理员", "学生管理员"]
        for i, name in enumerate(admin_names):
            admin_id = f"A{800001 + i}"  # 管理员工号: A800001, A800002, ...
            admin = Admin(
                id=admin_id,
                name=name,
                password="123456",
                dept="教务处",
                phone=f"139{i:08d}"
            )
            session.add(admin)
            admins.append(admin)
            
            # 同步创建 sys_users 记录
            result = await session.execute(select(User).where(User.username == admin_id))
            if not result.scalars().first():
                sys_user = User(username=admin_id, password="123456", role="admin")
                session.add(sys_user)
        
        await session.commit()
        print(f"Created {len(admins)} admins.")

        # 6. Create Students
        students = []
        for i in range(20):
            name = random.choice(STUDENT_NAMES_PREFIX) + random.choice(STUDENT_NAMES_SUFFIX)
            student = Student(
                id=f"2021{i:04d}",
                name=name,
                major=random.choice(MAJORS),
                grade=random.choice(["2021", "2022", "2023"]),
            )
            session.add(student)
            students.append(student)
        await session.commit()
        print(f"Created {len(students)} students.")

        # Ensure demo student exists in students table (20230001) and has data.
        await ensure_demo_student_data(session)

        # 7. Create Course Selections and Grades
        selections = []
        grades = []
        for student in students:
            # Each student selects 3-5 courses
            selected_courses = random.sample(courses, k=random.randint(3, 5))
            for course in selected_courses:
                # Course Selection
                selection = CourseSelection(
                    student_id=student.id,
                    course_id=course.id,
                    absent_count=random.randint(0, 3),
                    submit_homework_rate=random.uniform(0.8, 1.0)
                )
                session.add(selection)
                selections.append(selection)

                # Grade
                score = random.randint(60, 100)
                grade = Grade(
                    student_id=student.id,
                    course_id=course.id,
                    score=score,
                    exam_type="final"
                )
                session.add(grade)
                grades.append(grade)

        await session.commit()
        print(f"Created {len(selections)} course selections and {len(grades)} grades.")
        
        # 7. Create Teaching Management Test Data
        print("\n=== Creating Teaching Management Test Data ===")
        
        # 7.1 Create Leave Applications
        leave_apps = []
        for i, student in enumerate(students[:10]):  # First 10 students
            selected_courses = random.sample(courses, k=min(2, len(courses)))
            for course in selected_courses:
                if random.random() > 0.5:  # 50% chance
                    now = datetime.now()
                    leave_app = LeaveApply(
                        student_id=int(student.id),  # Convert string to int
                        course_id=course.id,
                        teacher_id=course.teacher_id,
                        type=random.choice(['病假', '事假', '其他']),
                        start_time=now + timedelta(days=random.randint(1, 7)),
                        end_time=now + timedelta(days=random.randint(8, 14)),
                        reason=random.choice([
                            '身体不适需要休息',
                            '家里有事需要请假',
                            '参加社团活动',
                            '参加学术会议'
                        ]),
                        status=random.choice(['pending', 'approved', 'rejected']),
                        opinion='同意请假' if random.random() > 0.5 else None
                    )
                    session.add(leave_app)
                    leave_apps.append(leave_app)
        await session.commit()
        print(f"Created {len(leave_apps)} leave applications.")
        
        # 7.2 Create Homework Assignments
        homeworks = []
        for i, course in enumerate(courses[:5]):  # First 5 courses
            for j in range(2):  # 2 homework per course
                homework = Homework(
                    title=f"{course.name} - 第{j+1}次作业",
                    course_id=course.id,
                    teacher_id=course.teacher_id,
                    content=f"完成课后习题 {j*5+1}-{j*5+5} 题",
                    deadline=datetime.now() + timedelta(days=random.randint(7, 14)),
                    type=random.choice(['主观题', '客观题', '文件提交']),
                    score=100
                )
                session.add(homework)
                homeworks.append(homework)
        await session.commit()
        print(f"Created {len(homeworks)} homework assignments.")
        
        # 7.3 Create Homework Submissions
        homework_submits = []
        for homework in homeworks:
            # Get students who selected this course
            result = await session.execute(
                select(CourseSelection).where(CourseSelection.course_id == homework.course_id)
            )
            course_selections = result.scalars().all()
            
            for selection in course_selections:
                if random.random() > 0.3:  # 70% submit rate
                    submit = HomeworkSubmit(
                        homework_id=homework.id,
                        student_id=int(selection.student_id),
                        content=random.choice([
                            '已完成，请老师查阅',
                            '作业已提交，附件见上传文件',
                            '完成所有习题，请审阅'
                        ]),
                        status=random.choice(['已提交', '已批改', '待提交']),
                        score=random.randint(70, 100) if random.random() > 0.5 else None,
                        comment='做得不错' if random.random() > 0.5 else None
                    )
                    session.add(submit)
                    homework_submits.append(submit)
        await session.commit()
        print(f"Created {len(homework_submits)} homework submissions.")
        
        # 7.4 Create Attendance Records
        attendance_records = []
        for course in courses[:5]:  # First 5 courses
            # Get students who selected this course
            result = await session.execute(
                select(CourseSelection).where(CourseSelection.course_id == course.id)
            )
            course_selections = result.scalars().all()
            
            for selection in course_selections:
                # Create 3 attendance records per student per course
                for _ in range(3):
                    record = Attendance(
                        course_id=course.id,
                        teacher_id=course.teacher_id,
                        student_id=int(selection.student_id),
                        status=random.choice(['已签到', '迟到', '未到', '请假']),
                        sign_time=datetime.now() - timedelta(days=random.randint(1, 30))
                    )
                    session.add(record)
                    attendance_records.append(record)
        await session.commit()
        print(f"Created {len(attendance_records)} attendance records.")
        
        # 7.5 Create Class Adjustment Requests
        class_adjusts = []
        for teacher in teachers:
            # Get teacher's courses
            result = await session.execute(
                select(Course).where(Course.teacher_id == teacher.id)
            )
            teacher_courses = result.scalars().all()
            
            if teacher_courses:
                course = random.choice(teacher_courses)
                adjust = ClassAdjust(
                    teacher_id=teacher.id,
                    course_id=course.id,
                    old_time=datetime.now() + timedelta(days=random.randint(1, 7)),
                    new_time=datetime.now() + timedelta(days=random.randint(8, 14)),
                    old_classroom='A101',
                    new_classroom='B202',
                    reason=random.choice([
                        '参加学术会议',
                        '教室设备维护',
                        '个人原因'
                    ]),
                    status=random.choice(['待审核', '已通过', '已拒绝'])
                )
                session.add(adjust)
                class_adjusts.append(adjust)
        await session.commit()
        print(f"Created {len(class_adjusts)} class adjustment requests.")
        
        # 7.6 Create Work Schedules
        work_schedules = []
        for teacher in teachers:
            for i in range(random.randint(3, 6)):
                schedule = WorkSchedule(
                    teacher_id=teacher.id,
                    time=datetime.now() + timedelta(days=i),
                    content=random.choice([
                        '高等数学 (1-2节)',
                        '教研室会议',
                        '值班',
                        '学生答疑'
                    ]),
                    type=random.choice(['上课', '开会', '值班', '其他']),
                    remark=random.choice(['教三-201', '会议室A', '办公室', None])
                )
                session.add(schedule)
                work_schedules.append(schedule)
        await session.commit()
        print(f"Created {len(work_schedules)} work schedules.")
        
        print("\n=== Teaching Management Data Initialization Completed! ===")

        print("Data initialization completed successfully!")

async def generate_classrooms_and_schedules(session, teachers):
    """Generate only classrooms and schedules if they're missing"""
    # Get existing courses
    result = await session.execute(select(Course))
    courses = result.scalars().all()
    
    if not courses:
        print("No courses found, cannot generate schedules.")
        return
    
    # Create Classrooms
    classrooms = []
    for name in CLASSROOM_NAMES:
        classroom = Classroom(
            name=name,
            capacity=random.choice([30, 40, 50, 60]),
            is_multimedia=random.choice([True, False])
        )
        session.add(classroom)
        await session.flush()
        session.add(
            ClassroomResource(
                classroom_id=classroom.id,
                code=f"CLS-{classroom.id:04d}",
                location=f"{name[0]}栋{name}",
                devices=json.dumps(["多媒体"]) if classroom.is_multimedia else None,
                status="idle",
            )
        )
        classrooms.append(classroom)
    await session.commit()
    print(f"Created {len(classrooms)} classrooms.")

    # Create Schedules
    schedules = []
    used_slots = set()
    
    for course in courses:
        slots_assigned = 0
        attempts = 0
        max_attempts = 50
        
        while slots_assigned < 2 and attempts < max_attempts:
            attempts += 1
            day = random.randint(0, 4)
            period = random.randint(0, 3)
            classroom = random.choice(classrooms)
            
            classroom_slot = (classroom.id, day, period)
            teacher_slot = (course.teacher_id, day, period)
            
            if classroom_slot not in used_slots and teacher_slot not in used_slots:
                schedule = Schedule(
                    course_id=course.id,
                    classroom_id=classroom.id,
                    teacher_id=course.teacher_id,
                    day=day,
                    period=period
                )
                session.add(schedule)
                schedules.append(schedule)
                used_slots.add(classroom_slot)
                used_slots.add(teacher_slot)
                slots_assigned += 1
    
    await session.commit()
    print(f"Created {len(schedules)} schedule entries.")

if __name__ == "__main__":
    async def create_tables():
         async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    asyncio.run(create_tables())
    asyncio.run(init_data())
