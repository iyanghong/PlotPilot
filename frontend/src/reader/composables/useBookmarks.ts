// frontend/src/reader/composables/useBookmarks.ts
import { ref } from 'vue'
import type { Bookmark } from '../types'

const STORAGE_KEY_PREFIX = 'plotpilot-reader-bookmarks'

function load(novelId: string): Bookmark[] {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}-${novelId}`)
    if (raw) {
      return JSON.parse(raw) as Bookmark[]
    }
  } catch {
    // ignore
  }
  return []
}

function save(novelId: string, bookmarks: Bookmark[]): void {
  try {
    localStorage.setItem(`${STORAGE_KEY_PREFIX}-${novelId}`, JSON.stringify(bookmarks))
  } catch {
    // 静默降级
  }
}

export function useBookmarks(novelId: string) {
  const bookmarks = ref<Bookmark[]>(load(novelId))

  function addBookmark(chapterNumber: number, chapterTitle: string): boolean {
    if (hasBookmark(chapterNumber)) return false
    const bm: Bookmark = {
      chapterNumber,
      chapterTitle,
      createdAt: Date.now(),
    }
    bookmarks.value.push(bm)
    save(novelId, bookmarks.value)
    return true
  }

  function removeBookmark(chapterNumber: number): boolean {
    const idx = bookmarks.value.findIndex((b) => b.chapterNumber === chapterNumber)
    if (idx === -1) return false
    bookmarks.value.splice(idx, 1)
    save(novelId, bookmarks.value)
    return true
  }

  function hasBookmark(chapterNumber: number): boolean {
    return bookmarks.value.some((b) => b.chapterNumber === chapterNumber)
  }

  function toggleBookmark(chapterNumber: number, chapterTitle: string): boolean {
    if (hasBookmark(chapterNumber)) {
      removeBookmark(chapterNumber)
      return false // now unbookmarked
    } else {
      addBookmark(chapterNumber, chapterTitle)
      return true // now bookmarked
    }
  }

  return { bookmarks, addBookmark, removeBookmark, hasBookmark, toggleBookmark }
}
