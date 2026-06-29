-- qoocommunity v0.1 Seed Data
-- PostgreSQL 16

-- ============================================================
-- 论坛分类
-- ============================================================
INSERT INTO forum_categories (name, slug, description, sort_order) VALUES
('综合讨论', 'general', 'QooBot 相关综合讨论区', 1),
('硬件开发', 'hardware', '硬件设计、传感器、执行器讨论', 2),
('软件开发', 'software', 'SDK、技能开发、系统集成', 3),
('技能分享', 'skills', '技能分享与展示', 4),
('社区公告', 'announcements', '官方公告与更新日志', 0),
('反馈建议', 'feedback', '功能请求与改进建议', 5);

-- ============================================================
-- 论坛标签
-- ============================================================
INSERT INTO forum_tags (name, slug, color) VALUES
('qoobrain', 'qoobrain', '#4CAF50'),
('qoobody', 'qoobody', '#FF9800'),
('qoosvc', 'qoosvc', '#2196F3'),
('qoodev', 'qoodev', '#9C27B0'),
('入门', 'getting-started', '#00BCD4'),
('高级', 'advanced', '#F44336'),
('教程', 'tutorial', '#8BC34A'),
('问题', 'question', '#FF5722'),
('展示', 'showcase', '#795548'),
('公告', 'announcement', '#607D8B');

-- ============================================================
-- 学院认证
-- ============================================================
INSERT INTO academy_certifications (name, slug, level, description, exam_duration, pass_score, question_count) VALUES
('QooBot Developer', 'qoobot-developer', 'BEGINNER', 'QooBot 初级开发者认证，涵盖基础概念与 SDK 使用', 60, 70, 50),
('QooBot Advanced Developer', 'qoobot-advanced', 'ADVANCED', 'QooBot 高级开发者认证，涵盖系统集成与高级功能', 90, 75, 60),
('QooBot Expert', 'qoobot-expert', 'EXPERT', 'QooBot 专家认证，涵盖核心贡献与架构设计', 120, 80, 70);

-- ============================================================
-- 学习路径种子数据
-- ============================================================
INSERT INTO academy_learning_paths (title, slug, description, cover_url, level, course_count, sort_order, is_published, created_at, updated_at)
VALUES 
('QooBot 入门基础', 'qoobot-basics', '从零开始了解 QooBot 机器人平台，掌握基础概念和开发环境搭建。', '/images/learning-paths/basics.png', 'BEGINNER', 3, 1, TRUE, NOW(), NOW()),
('技能开发实战', 'skill-development', '深入学习 QooBot 技能开发，从简单的服务机器人到复杂的交互式应用。', '/images/learning-paths/skills.png', 'INTERMEDIATE', 4, 2, TRUE, NOW(), NOW()),
('机器人系统进阶', 'advanced-robotics', '掌握机器人操作系统核心原理、运动规划、传感器融合等高级主题。', '/images/learning-paths/advanced.png', 'ADVANCED', 4, 3, TRUE, NOW(), NOW()),
('AI 与感知', 'ai-perception', '学习计算机视觉、语音识别、自然语言处理在机器人上的应用。', '/images/learning-paths/ai.png', 'ADVANCED', 3, 4, TRUE, NOW(), NOW()),
('硬件与嵌入式', 'hardware-embedded', '了解 QooBot 硬件架构、传感器接口、嵌入式系统开发。', '/images/learning-paths/hardware.png', 'INTERMEDIATE', 3, 5, TRUE, NOW(), NOW())
ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- 贡献者等级说明
-- ============================================================
-- Contributor → Maintainer → Committer → TSC Member
-- 自动化晋升条件由 LevelEvaluationService 实现
