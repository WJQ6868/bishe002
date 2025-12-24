import os
import sqlite3

DEMO_STUDENT_ID = "20230001"


def _scalar(cur: sqlite3.Cursor, sql: str, params: tuple = ()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else None


def main() -> int:
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "edu_system.db"),
        os.path.join(os.path.dirname(__file__), "edu_system.db"),
    ]

    found_any = False
    for db_path in candidates:
        if not os.path.exists(db_path):
            continue
        found_any = True
        print(f"\nDB: {db_path}")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        try:
            print("sys_users(20230001)=", _scalar(cur, "select count(*) from sys_users where username=?", (DEMO_STUDENT_ID,)))
            print("students(20230001)=", _scalar(cur, "select count(*) from students where id=?", (DEMO_STUDENT_ID,)))
            print(
                "course_selections(20230001)=",
                _scalar(cur, "select count(*) from course_selections where student_id=?", (DEMO_STUDENT_ID,)),
            )
            print("grades(20230001)=", _scalar(cur, "select count(*) from grades where student_id=?", (DEMO_STUDENT_ID,)))

            cur.execute(
                "select course_id from course_selections where student_id=? order by course_id limit 10",
                (DEMO_STUDENT_ID,),
            )
            print("selected_course_ids=", [r[0] for r in cur.fetchall()])
        finally:
            conn.close()

    if not found_any:
        print("未找到 edu_system.db（候选路径都不存在）")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
