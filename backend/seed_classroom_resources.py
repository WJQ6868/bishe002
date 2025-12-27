import json
import os
import sqlite3
from typing import Any


def _find_db_path() -> str:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    candidates = [
        os.path.join(repo_root, "edu_system.db"),
        os.path.join(os.path.dirname(__file__), "edu_system.db"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[-1]


def _ensure_tables(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS classrooms (
            id INTEGER PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            capacity INTEGER NOT NULL,
            is_multimedia BOOLEAN DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS classroom_resources (
            id INTEGER PRIMARY KEY,
            classroom_id INTEGER NOT NULL UNIQUE,
            code VARCHAR(50) UNIQUE,
            location VARCHAR(100),
            devices TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'idle',
            remark VARCHAR(255),
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE
        )
        """
    )


def _upsert_classroom(con: sqlite3.Connection, *, name: str, capacity: int, is_multimedia: bool) -> int:
    cur = con.cursor()
    row = cur.execute("SELECT id FROM classrooms WHERE name = ?", (name,)).fetchone()
    if row:
        classroom_id = int(row[0])
        cur.execute(
            "UPDATE classrooms SET capacity = ?, is_multimedia = ? WHERE id = ?",
            (int(capacity), 1 if is_multimedia else 0, classroom_id),
        )
        return classroom_id

    cur.execute(
        "INSERT INTO classrooms(name, capacity, is_multimedia) VALUES (?, ?, ?)",
        (name, int(capacity), 1 if is_multimedia else 0),
    )
    return int(cur.lastrowid)


def _upsert_resource(
    con: sqlite3.Connection,
    *,
    classroom_id: int,
    code: str,
    location: str,
    devices: list[str],
    status: str,
    remark: str,
) -> None:
    cur = con.cursor()

    # Code uniqueness guard
    code_row = cur.execute(
        "SELECT classroom_id FROM classroom_resources WHERE code = ?",
        (code,),
    ).fetchone()
    if code_row and int(code_row[0]) != int(classroom_id):
        raise SystemExit(
            f"编号 {code} 已被教室ID={int(code_row[0])}占用，无法绑定到教室ID={classroom_id}。"
        )

    existing = cur.execute(
        "SELECT id, code FROM classroom_resources WHERE classroom_id = ?",
        (int(classroom_id),),
    ).fetchone()

    devices_json = json.dumps(devices, ensure_ascii=False)

    if existing:
        resource_id = int(existing[0])
        cur.execute(
            """
            UPDATE classroom_resources
            SET code = ?, location = ?, devices = ?, status = ?, remark = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (code, location, devices_json, status, remark, resource_id),
        )
        return

    cur.execute(
        """
        INSERT INTO classroom_resources(classroom_id, code, location, devices, status, remark)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (int(classroom_id), code, location, devices_json, status, remark),
    )


def main() -> None:
    db_path = _find_db_path()
    print(f"[seed] db={db_path}")

    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA foreign_keys = ON")
        _ensure_tables(con)

        rooms: list[dict[str, Any]] = [
            {
                "code": "CLS-5192731",
                "name": "计算机专业教室101",
                "capacity": 40,
                "location": "实训楼3层301室",
                "devices": ["多媒体", "空调", "投影仪"],
                "remark": "计算机网络技术专业授课用",
            },
            {
                "code": "CLS-5192732",
                "name": "软件工程教室102",
                "capacity": 45,
                "location": "实训楼3层302室",
                "devices": ["多媒体", "空调", "投影仪", "音响"],
                "remark": "软件工程专业实训用",
            },
            {
                "code": "CLS-5192733",
                "name": "网络安全教室201",
                "capacity": 30,
                "location": "实训楼4层401室",
                "devices": ["多媒体", "空调", "投影仪", "防火墙设备"],
                "remark": "网络安全专业实验用",
            },
            {
                "code": "CLS-5192734",
                "name": "人工智能教室202",
                "capacity": 35,
                "location": "实训楼4层402室",
                "devices": ["多媒体", "空调", "投影仪", "AI实训主机"],
                "remark": "人工智能专业实践用",
            },
            {
                "code": "CLS-5192735",
                "name": "大数据教室301",
                "capacity": 50,
                "location": "实训楼5层501室",
                "devices": ["多媒体", "空调", "投影仪", "服务器集群"],
                "remark": "大数据专业授课用",
            },
            {
                "code": "CLS-5192736",
                "name": "工业互联网教室302",
                "capacity": 40,
                "location": "实训楼5层502室",
                "devices": ["多媒体", "空调", "投影仪", "工业网关设备"],
                "remark": "工业互联网专业实训用",
            },
            {
                "code": "CLS-5192737",
                "name": "公共机房401",
                "capacity": 60,
                "location": "实训楼6层601室",
                "devices": ["多媒体", "空调", "投影仪", "公共电脑"],
                "remark": "全专业公共课程用",
            },
            {
                "code": "CLS-5192738",
                "name": "项目研讨室501",
                "capacity": 20,
                "location": "实训楼7层701室",
                "devices": ["多媒体", "空调", "投影仪", "圆桌会议桌"],
                "remark": "专业项目研讨用",
            },
            {
                "code": "CLS-5192739",
                "name": "备用教室601",
                "capacity": 45,
                "location": "实训楼8层801室",
                "devices": ["多媒体", "空调", "投影仪"],
                "remark": "课程调课备用",
            },
            {
                "code": "CLS-5192740",
                "name": "综合实验教室602",
                "capacity": 35,
                "location": "实训楼8层802室",
                "devices": ["多媒体", "空调", "投影仪", "多专业实验设备"],
                "remark": "跨专业综合实验用",
            },
        ]

        for idx, room in enumerate(rooms, start=1):
            is_multimedia = "多媒体" in room["devices"]
            classroom_id = _upsert_classroom(
                con,
                name=room["name"],
                capacity=int(room["capacity"]),
                is_multimedia=is_multimedia,
            )
            _upsert_resource(
                con,
                classroom_id=classroom_id,
                code=room["code"],
                location=room["location"],
                devices=room["devices"],
                status="idle",
                remark=room["remark"],
            )
            print(f"[seed] {idx}/10 ok: id={classroom_id} code={room['code']} name={room['name']}")

        con.commit()

        rows = con.execute(
            """
            SELECT r.code, c.name, c.capacity, r.location, r.devices, r.status, r.remark
            FROM classroom_resources r
            JOIN classrooms c ON c.id = r.classroom_id
            WHERE r.code BETWEEN 'CLS-5192731' AND 'CLS-5192740'
            ORDER BY r.code
            """
        ).fetchall()

        print("\n[seed] verify rows:")
        for code, name, capacity, location, devices, status, remark in rows:
            devices_list = json.loads(devices) if devices else []
            print(f"- {code} | {name} | {capacity} | {location} | {devices_list} | {status} | {remark}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
