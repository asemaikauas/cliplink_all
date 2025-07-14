-- Sample Queries for Cliplink AI Database
-- This file demonstrates common operations for the Cliplink AI application

-- 1. Create a new user
INSERT INTO users (email, password_hash) 
VALUES ('user@example.com', '$2b$12$hashed_password_here');

-- 2. Submit a new YouTube video for processing
INSERT INTO videos (user_id, youtube_id, title) 
VALUES (
    (SELECT id FROM users WHERE email = 'user@example.com'),
    'dQw4w9WgXcQ',
    'Never Gonna Give You Up'
);

-- 3. Update video status during processing
UPDATE videos 
SET status = 'processing' 
WHERE youtube_id = 'dQw4w9WgXcQ';

-- 4. Add clips for a processed video
INSERT INTO clips (video_id, s3_url, start_time, end_time, duration)
VALUES 
    (
        (SELECT id FROM videos WHERE youtube_id = 'dQw4w9WgXcQ'),
        'https://s3.amazonaws.com/cliplink-bucket/clip1.mp4',
        15.5,
        30.2,
        14.7
    ),
    (
        (SELECT id FROM videos WHERE youtube_id = 'dQw4w9WgXcQ'),
        'https://s3.amazonaws.com/cliplink-bucket/clip2.mp4',
        45.0,
        62.3,
        17.3
    );

-- 5. Mark video as completed
UPDATE videos 
SET status = 'done' 
WHERE youtube_id = 'dQw4w9WgXcQ';

-- 6. Get user's dashboard: all videos and their clips
SELECT 
    v.id as video_id,
    v.youtube_id,
    v.title,
    v.status,
    v.created_at as video_created_at,
    c.id as clip_id,
    c.s3_url,
    c.start_time,
    c.end_time,
    c.duration,
    c.created_at as clip_created_at
FROM videos v
LEFT JOIN clips c ON v.id = c.video_id
WHERE v.user_id = (SELECT id FROM users WHERE email = 'user@example.com')
ORDER BY v.created_at DESC, c.created_at ASC;

-- 7. Get clips for a specific video
SELECT 
    c.id,
    c.s3_url,
    c.start_time,
    c.end_time,
    c.duration,
    c.created_at
FROM clips c
JOIN videos v ON c.video_id = v.id
WHERE v.youtube_id = 'dQw4w9WgXcQ'
ORDER BY c.start_time ASC;

-- 8. Log a clip view
INSERT INTO clip_view_logs (user_id, clip_id)
VALUES (
    (SELECT id FROM users WHERE email = 'user@example.com'),
    (SELECT id FROM clips WHERE s3_url = 'https://s3.amazonaws.com/cliplink-bucket/clip1.mp4')
);

-- 9. Get analytics: most viewed clips
SELECT 
    c.id,
    c.s3_url,
    v.title as video_title,
    v.youtube_id,
    COUNT(cvl.id) as view_count,
    MAX(cvl.viewed_at) as last_viewed
FROM clips c
JOIN videos v ON c.video_id = v.id
LEFT JOIN clip_view_logs cvl ON c.id = cvl.clip_id
GROUP BY c.id, c.s3_url, v.title, v.youtube_id
ORDER BY view_count DESC
LIMIT 10;

-- 10. Get user's video processing status summary
SELECT 
    status,
    COUNT(*) as count
FROM videos
WHERE user_id = (SELECT id FROM users WHERE email = 'user@example.com')
GROUP BY status;

-- 11. Clean up failed videos older than 7 days
DELETE FROM videos 
WHERE status = 'failed' 
AND created_at < NOW() - INTERVAL '7 days';

-- 12. Get videos that are stuck in processing (older than 1 hour)
SELECT 
    v.id,
    v.youtube_id,
    v.title,
    v.created_at,
    u.email
FROM videos v
JOIN users u ON v.user_id = u.id
WHERE v.status = 'processing' 
AND v.created_at < NOW() - INTERVAL '1 hour';

-- 13. Get user activity report
SELECT 
    DATE(cvl.viewed_at) as view_date,
    COUNT(*) as clips_viewed,
    COUNT(DISTINCT cvl.clip_id) as unique_clips_viewed
FROM clip_view_logs cvl
WHERE cvl.user_id = (SELECT id FROM users WHERE email = 'user@example.com')
AND cvl.viewed_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(cvl.viewed_at)
ORDER BY view_date DESC;

-- 14. Get storage usage per user (count of clips)
SELECT 
    u.email,
    COUNT(c.id) as total_clips,
    SUM(c.duration) as total_duration_seconds
FROM users u
LEFT JOIN videos v ON u.id = v.user_id
LEFT JOIN clips c ON v.id = c.video_id
GROUP BY u.id, u.email
ORDER BY total_clips DESC; 