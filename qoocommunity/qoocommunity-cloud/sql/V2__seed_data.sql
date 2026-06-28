-- qoocommunity v0.1 Seed Data

-- ============================================================
-- 论坛分类
-- ============================================================
INSERT INTO forum_categories (name, slug, description, sort_order) VALUES
('General Discussion', 'general', 'General topics about QooBot', 1),
('Hardware', 'hardware', 'Hardware design, assembly, and modifications', 2),
('Software & SDK', 'software', 'QooBrain SDK, APIs, and software development', 3),
('Skills Development', 'skills', 'Creating and sharing robot skills', 4),
('Simulation', 'simulation', 'QooDev simulation and digital twin', 5),
('Integration', 'integration', 'Integrating QooBot with other systems', 6),
('Showcase', 'showcase', 'Show off your QooBot projects', 7),
('Community & Events', 'community', 'Events, meetups, and community news', 8);

-- ============================================================
-- 论坛标签
-- ============================================================
INSERT INTO forum_tags (name, slug, color) VALUES
('python', 'python', '#3572A5'),
('cpp', 'cpp', '#f34b7d'),
('ros2', 'ros2', '#2233AA'),
('hardware', 'hardware', '#fbca04'),
('perception', 'perception', '#006b75'),
('planning', 'planning', '#d73a4a'),
('control', 'control', '#0075ca'),
('skill-dev', 'skill-dev', '#5319e7'),
('beginner', 'beginner', '#0e8a16'),
('advanced', 'advanced', '#b60205'),
('question', 'question', '#cc317c'),
('tutorial', 'tutorial', '#1d76db');

-- ============================================================
-- 学院认证
-- ============================================================
INSERT INTO academy_certifications (name, slug, level, description, exam_duration, pass_score, question_count) VALUES
('QooBot Certified Developer', 'qcd', 'DEVELOPER', 'Basic knowledge of QooBot platform, SDK usage, and skill development fundamentals', 60, 70, 50),
('QooBot Certified Advanced Developer', 'qcad', 'ADVANCED', 'Advanced system integration, perception pipeline, planning algorithms, and deployment', 90, 75, 60),
('QooBot Certified Expert', 'qce', 'EXPERT', 'Core contribution level: kernel, drivers, real-time systems, and architecture design', 120, 80, 70);
