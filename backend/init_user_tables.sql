-- 1. Clean up existing data
DELETE FROM sys_users WHERE username IN ('admin', '800001', 'T1001', 'T2001', '1001', '100001', 'S2024001', '20230001');
DELETE FROM user_profiles WHERE user_id NOT IN (SELECT id FROM sys_users);
DELETE FROM students WHERE id IN ('S2024001', '1001', '20230001');
DELETE FROM teachers WHERE id IN ('T1001', 'T2001', '100001');
DELETE FROM admins WHERE id IN ('admin', '800001');

-- 2. Insert System Users (Password is '123456' hashed with bcrypt)
-- Hash reused across demo accounts for consistency
INSERT INTO sys_users (username, password, role, is_active) VALUES 
('admin', '$2b$12$r8NJfA6XJOaGmVqoAuvfwuPyauIF2SmdX0nNu/yIObY77N0mDIr1m', 'admin', 1),
('800001', '$2b$12$r8NJfA6XJOaGmVqoAuvfwuPyauIF2SmdX0nNu/yIObY77N0mDIr1m', 'admin', 1),
('T2001', '$2b$12$r8NJfA6XJOaGmVqoAuvfwuPyauIF2SmdX0nNu/yIObY77N0mDIr1m', 'teacher', 1),
('100001', '$2b$12$r8NJfA6XJOaGmVqoAuvfwuPyauIF2SmdX0nNu/yIObY77N0mDIr1m', 'teacher', 1),
('1001', '$2b$12$r8NJfA6XJOaGmVqoAuvfwuPyauIF2SmdX0nNu/yIObY77N0mDIr1m', 'student', 1),
('20230001', '$2b$12$r8NJfA6XJOaGmVqoAuvfwuPyauIF2SmdX0nNu/yIObY77N0mDIr1m', 'student', 1);

-- 3. Insert User Profiles
INSERT INTO user_profiles (user_id, name, dept, grade, entry_time, create_time) 
SELECT id, 'Platform Admin', 'IT Dept', NULL, '2020-01-01', datetime('now') FROM sys_users WHERE username = 'admin';

INSERT INTO user_profiles (user_id, name, dept, grade, entry_time, create_time) 
SELECT id, 'Admin Office', 'Academic Affairs', NULL, '2020-01-01', datetime('now') FROM sys_users WHERE username = '800001';

INSERT INTO user_profiles (user_id, name, dept, grade, entry_time, create_time) 
SELECT id, 'Zhang Teacher', 'CS Dept', NULL, '2021-09-01', datetime('now') FROM sys_users WHERE username = 'T2001';

INSERT INTO user_profiles (user_id, name, dept, grade, entry_time, create_time) 
SELECT id, 'Teacher Zhang', 'Computer Science', NULL, '2021-09-01', datetime('now') FROM sys_users WHERE username = '100001';

INSERT INTO user_profiles (user_id, name, dept, grade, entry_time, create_time) 
SELECT id, 'Li Student', 'CS Dept', '2024', '2024-09-01', datetime('now') FROM sys_users WHERE username = '1001';

INSERT INTO user_profiles (user_id, name, dept, grade, entry_time, create_time) 
SELECT id, 'Student Li', 'Computer Science', '2023', '2023-09-01', datetime('now') FROM sys_users WHERE username = '20230001';

-- 4. Insert Role Specific Data
INSERT INTO admins (id, name, dept, phone) VALUES 
('admin', 'Platform Admin', 'IT Dept', '13800138000'),
('800001', 'Admin Office', 'Academic Affairs', '13800000001');

INSERT INTO teachers (id, name) VALUES 
('T2001', 'Zhang Teacher'),
('100001', 'Teacher Zhang');

INSERT INTO students (id, name, major, grade) VALUES 
('1001', 'Li Student', 'Computer Science', '2024'),
('20230001', 'Student Li', 'Computer Science', '2023');
