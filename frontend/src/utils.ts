export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })
}

export const repeatLabels: Record<string, string> = {
  none: '只提醒一次',
  daily: '每天',
  weekly: '每周',
  weekdays: '工作日',
}

export const callStatusLabels: Record<string, string> = {
  initiated: '已发起',
  completed: '已接通',
  failed: '未接通',
  cancelled: '已取消',
}

export const confirmationKindLabels: Record<string, string> = {
  medical_memory: '健康信息',
  identity_memory: '身份信息',
  memory_change: '记忆修改',
  other: '其他',
}

export const memoryKindLabels: Record<string, string> = {
  fact: '事实',
  preference: '喜好',
  medical: '健康',
  identity: '身份',
  event: '事情',
}
