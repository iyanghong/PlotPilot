// frontend/src/api/reader.ts
import { apiClient } from './config'
import { apiRoutes } from './endpoints'
import type { ChapterMeta, ChapterContent } from '@/reader/types'

/**
 * GET /api/v1/novels/{novelId}/chapters
 * 返回章节目录（不含正文）
 */
export function listChapters(novelId: string): Promise<ChapterMeta[]> {
  return apiClient.get<ChapterMeta[]>(apiRoutes.novels.chaptersClient(novelId)) as Promise<ChapterMeta[]>
}

/**
 * GET /api/v1/novels/{novelId}/chapters/{chapterNumber}
 * 返回指定章节正文
 */
export function getChapter(novelId: string, chapterNumber: number): Promise<ChapterContent> {
  return apiClient.get<ChapterContent>(
    apiRoutes.novels.chaptersClient(novelId) + '/' + encodeURIComponent(chapterNumber)
  ) as Promise<ChapterContent>
}
