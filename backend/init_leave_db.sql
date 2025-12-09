-- Database Initialization Script for Leave Module

-- Create leave_apply table
CREATE TABLE IF NOT EXISTS leave_apply (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    teacher_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    type VARCHAR(20) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    reason TEXT NOT NULL,
    file_url VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    opinion TEXT,
    approve_time TIMESTAMP,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(student_id) REFERENCES sys_users(id),
    FOREIGN KEY(teacher_id) REFERENCES sys_users(id),
    FOREIGN KEY(course_id) REFERENCES courses(id)
);

-- Insert Test Leave Applications
-- Ensure users and courses exist first (from init_user_tables.sql and below)

-- Insert a test course if not exists (Course ID 101)
INSERT OR IGNORE INTO courses (id, name, teacher_id, credit, capacity, course_type) VALUES (101, 'Software Engineering', 'T2001', 4, 60, '必修');

-- Insert Course Selection for student 1001
INSERT OR IGNORE INTO course_selections (student_id, course_id) VALUES ('1001', 101);

-- Get User IDs for student and teacher
-- Assuming init_user_tables.sql set:
-- Student '1001' has sys_user.id (need to fetch dynamically or assume ID if auto-increment is predictable?)
-- Auto-increment IDs are hard to predict if deletions happened.
-- Ideally we use subqueries but SQLite support varies.

-- Let's just use the subquery syntax which is supported in INSERT
INSERT INTO leave_apply (student_id, teacher_id, course_id, type, start_time, end_time, reason, status, create_time)
SELECT 
    s.id, t.id, 101, 'sick', 
    datetime('now', '+1 day'), datetime('now', '+2 days'), 
    'Feeling unwell', 'pending', datetime('now')
FROM sys_users s, sys_users t
WHERE s.username = '1001' AND t.username = 'T2001'
AND NOT EXISTS (SELECT 1 FROM leave_apply WHERE reason = 'Feeling unwell');

INSERT INTO leave_apply (student_id, teacher_id, course_id, type, start_time, end_time, reason, status, create_time)
SELECT 
    s.id, t.id, 101, 'personal', 
    datetime('now', '-5 days'), datetime('now', '-3 days'), 
    'Family matter', 'approved', datetime('now', '-6 days')
FROM sys_users s, sys_users t
WHERE s.username = '1001' AND t.username = 'T2001'
AND NOT EXISTS (SELECT 1 FROM leave_apply WHERE reason = 'Family matter');

INSERT INTO leave_apply (student_id, teacher_id, course_id, type, start_time, end_time, reason, status, create_time)
SELECT 
    s.id, t.id, 101, 'sick', 
    datetime('now', '-10 days'), datetime('now', '-9 days'), 
    'Fever', 'rejected', datetime('now', '-11 days')
FROM sys_users s, sys_users t
WHERE s.username = '1001' AND t.username = 'T2001'
AND NOT EXISTS (SELECT 1 FROM leave_apply WHERE reason = 'Fever');
