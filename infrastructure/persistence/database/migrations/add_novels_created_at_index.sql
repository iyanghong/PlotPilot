-- 为 novels.created_at 添加索引，加速列表页 ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_novels_created_at ON novels(created_at);
