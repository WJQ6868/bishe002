import argparse
import os
import sqlite3
from typing import Iterable


DEMO_CLASS_CODES = [
    "计网2301",
    "计网2302",
    "软工2301",
    "软工2302",
    "网安2301",
    "网安2302",
    "AI2301",
    "AI2302",
    "大数据2301",
    "大数据2302",
    "工互2301",
    "工互2302",
]

# These names were used by the earlier demo seeding.
DEMO_STUDENT_NAMES = ["张三", "李四", "王五", "赵六", "孙七"]

# These numeric prefixes were used by the earlier demo seeding (see student_base in app startup).
DEMO_STUDENT_PREFIXES = [
    "2301",
    "2302",
    "2311",
    "2312",
    "2321",
    "2322",
    "2331",
    "2332",
    "2341",
    "2342",
    "2351",
    "2352",
]


def _candidates() -> list[str]:
    return [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "edu_system.db"),
        os.path.join(os.path.dirname(__file__), "edu_system.db"),
    ]


def _print_sample(rows: Iterable[tuple], limit: int = 10) -> None:
    rows = list(rows)
    for r in rows[:limit]:
        print("  ", r)
    if len(rows) > limit:
        print(f"  ... ({len(rows) - limit} more)")


def main() -> int:
    parser = argparse.ArgumentParser(description="清理演示班级/学生数据（默认 dry-run，只打印不删除）")
    parser.add_argument("--db", dest="db_path", default=None, help="指定 edu_system.db 路径")
    parser.add_argument("--yes", action="store_true", help="确认执行删除（否则只 dry-run）")
    args = parser.parse_args()

    db_paths = [args.db_path] if args.db_path else _candidates()
    db_paths = [p for p in db_paths if p]

    found = False
    for db_path in db_paths:
        if not os.path.exists(db_path):
            continue
        found = True
        print(f"\nDB: {db_path}")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        try:
            placeholders = ",".join(["?"] * len(DEMO_CLASS_CODES))
            cur.execute(
                f"""
                select id, name, code, major_id
                from academic_classes
                where name in ({placeholders})
                   or code in ({placeholders})
                order by id
                """,
                tuple(DEMO_CLASS_CODES + DEMO_CLASS_CODES),
            )
            class_rows = cur.fetchall()
            class_ids = [int(r["id"]) for r in class_rows]

            print(f"命中疑似演示班级数: {len(class_ids)}")
            _print_sample([(r["id"], r["name"], r["code"], r["major_id"]) for r in class_rows])

            if not class_ids:
                print("未发现匹配的演示班级，跳过。")
                continue

            class_placeholders = ",".join(["?"] * len(class_ids))
            name_placeholders = ",".join(["?"] * len(DEMO_STUDENT_NAMES))
            like_clauses = " or ".join(["student_code like ?" for _ in DEMO_STUDENT_PREFIXES])
            like_params = [f"{p}%" for p in DEMO_STUDENT_PREFIXES]

            cur.execute(
                f"""
                select id, student_code, name, class_id
                from academic_students
                where class_id in ({class_placeholders})
                  and name in ({name_placeholders})
                  and ({like_clauses})
                order by class_id, student_code
                """,
                tuple(class_ids + DEMO_STUDENT_NAMES + like_params),
            )
            student_rows = cur.fetchall()

            print(f"命中疑似演示学生数: {len(student_rows)}")
            _print_sample([(r["id"], r["student_code"], r["name"], r["class_id"]) for r in student_rows])

            if not args.yes:
                print("dry-run: 未执行删除（加 --yes 才会删除）")
                continue

            conn.execute("begin")

            student_ids = [int(r["id"]) for r in student_rows]
            if student_ids:
                stu_placeholders = ",".join(["?"] * len(student_ids))
                cur.execute(
                    f"delete from academic_students where id in ({stu_placeholders})",
                    tuple(student_ids),
                )
                print(f"已删除学生: {cur.rowcount}")
            else:
                print("未匹配到可删除的演示学生（不会删除任何学生）")

            deleted_classes = 0
            for cid in class_ids:
                cur.execute("select count(*) from academic_students where class_id=?", (cid,))
                remaining = int(cur.fetchone()[0])
                if remaining == 0:
                    cur.execute("delete from academic_classes where id=?", (cid,))
                    if cur.rowcount:
                        deleted_classes += 1
                else:
                    try:
                        cur.execute("update academic_classes set student_count=? where id=?", (remaining, cid))
                    except sqlite3.OperationalError:
                        pass

            print(f"已删除班级: {deleted_classes}")

            conn.commit()
            print("清理完成")

        finally:
            conn.close()

    if not found:
        print("未找到 edu_system.db（候选路径都不存在），可用 --db 指定路径")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
