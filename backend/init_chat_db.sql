-- Database Initialization Script for Chat Module

-- Create chat_message table
CREATE TABLE IF NOT EXISTS chat_message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id INTEGER NOT NULL,
    from_role VARCHAR(20) NOT NULL,
    to_id INTEGER NOT NULL,
    to_role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    type VARCHAR(20) DEFAULT 'text',
    send_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER DEFAULT 0
);

-- Create user_status table
CREATE TABLE IF NOT EXISTS user_status (
    user_id INTEGER PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'offline' NOT NULL,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert Test Messages (English to avoid encoding issues in shell pipe)
INSERT INTO chat_message (from_id, from_role, to_id, to_role, content, type, send_time, is_read) VALUES 
(1001, 'student', 2001, 'teacher', 'Hello teacher, what is the exam scope?', 'text', datetime('now', '-1 hour'), 1),
(2001, 'teacher', 1001, 'student', 'Hi, it covers the first 5 chapters.', 'text', datetime('now', '-55 minutes'), 1),
(1001, 'student', 2001, 'teacher', 'Okay, thank you!', 'text', datetime('now', '-50 minutes'), 1),
(2001, 'teacher', 1001, 'student', 'You are welcome.', 'text', datetime('now', '-45 minutes'), 0),
(1001, 'student', 2001, 'teacher', 'One more thing, when is the report due?', 'text', datetime('now', '-5 minutes'), 0);

-- Insert Test User Status
INSERT INTO user_status (user_id, status, update_time) VALUES 
(1001, 'online', datetime('now')),
(2001, 'away', datetime('now'));
