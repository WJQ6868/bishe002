-- Database Initialization Script for Friend System
-- 好友系统数据库初始化脚本
-- Create friend_request table (好友申请表)
CREATE TABLE IF NOT EXISTS friend_request (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user_id INTEGER NOT NULL,
    -- 发起申请的用户ID
    to_user_id INTEGER NOT NULL,
    -- 被申请的用户ID
    message TEXT,
    -- 申请附加消息
    status VARCHAR(20) DEFAULT 'pending',
    -- 状态: pending, accepted, rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_user_id) REFERENCES user(id),
    FOREIGN KEY (to_user_id) REFERENCES user(id)
);
-- Create friendship table (好友关系表)
-- 采用规范化设计: user_id_1 < user_id_2，避免重复记录
CREATE TABLE IF NOT EXISTS friendship (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id_1 INTEGER NOT NULL,
    -- 用户1 ID (较小的ID)
    user_id_2 INTEGER NOT NULL,
    -- 用户2 ID (较大的ID)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id_1) REFERENCES user(id),
    FOREIGN KEY (user_id_2) REFERENCES user(id),
    UNIQUE(user_id_1, user_id_2) -- 防止重复好友关系
);
-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_friend_request_to ON friend_request(to_user_id, status);
CREATE INDEX IF NOT EXISTS idx_friend_request_from ON friend_request(from_user_id);
CREATE INDEX IF NOT EXISTS idx_friendship_user1 ON friendship(user_id_1);
CREATE INDEX IF NOT EXISTS idx_friendship_user2 ON friendship(user_id_2);
-- Insert test data (optional, for development)
-- 测试数据可在开发环境使用