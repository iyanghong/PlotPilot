/** 小说数据导出/导入 API — 作者：Axelton */

/** 备份下载超时时间：10 分钟（大部头小说导出数据量大） */
const BACKUP_DOWNLOAD_TIMEOUT_MS = 10 * 60 * 1000

/** 导出小说备份 ZIP — 触发浏览器下载 */
export async function downloadBackup(novelId: string): Promise<void> {
  const token = localStorage.getItem('token')
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), BACKUP_DOWNLOAD_TIMEOUT_MS)

  try {
    const res = await fetch(`/api/v1/backup/novel/${novelId}`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
    if (!res.ok) {
      const msg = await res.text().catch(() => '')
      throw new Error(msg || '导出失败')
    }
    // IMPORTANT: read headers BEFORE consuming body with blob()
    const disposition = res.headers.get('Content-Disposition') || ''
    const match = disposition.match(/filename="(.+)"/)
    const filename = match?.[1] || 'backup.zip'

    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    if (e?.name === 'AbortError') {
      throw new Error('备份下载超时（10分钟），大部头小说请耐心等待或联系管理员')
    }
    throw e
  } finally {
    clearTimeout(timeoutId)
  }
}

/** 导入小说备份 ZIP（覆盖已有小说） */
export async function uploadBackup(
  novelId: string,
  file: File,
): Promise<{ success: boolean; stats: Record<string, number> }> {
  const formData = new FormData()
  formData.append('file', file)
  const token = localStorage.getItem('token')
  const res = await fetch(`/api/v1/backup/novel/${novelId}/restore`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })
  if (!res.ok) {
    const msg = await res.text().catch(() => '')
    throw new Error(msg || '导入失败')
  }
  return res.json()
}

/** 从备份 ZIP 创建新小说（跨实例导入，无需已有小说） */
export async function uploadBackupAsNew(
  file: File,
): Promise<{ success: boolean; novel_id: string; stats: Record<string, number> }> {
  const formData = new FormData()
  formData.append('file', file)
  const token = localStorage.getItem('token')
  const res = await fetch('/api/v1/backup/restore', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })
  if (!res.ok) {
    const msg = await res.text().catch(() => '')
    throw new Error(msg || '导入失败')
  }
  return res.json()
}
