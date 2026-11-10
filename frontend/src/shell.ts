/**
 * 平板壳（Android / 未来的鸿蒙）与网页之间的唯一桥接层。
 *
 * 原生侧统一注入 `window.Shell`，方法签名两个平台保持一致：
 *   shellVersion(): string
 *   serverUrl(): string
 *   speak(text: string): void
 *   stopSpeaking(): void
 *   startListening(): boolean        // false 表示语音识别不可用
 *   stopListening(): void
 *   callNumber(phone: string): void
 *   openUpdate(url: string): void
 *
 * 原生 → 网页的回调（由壳主动调用，网页只负责接收）：
 *   window.onShellAsrResult(text: string)
 *   window.onShellAsrError(message: string)
 *   window.onShellSpeakState(state: 'start' | 'done')
 *
 * 浏览器里没有 `window.Shell` 时，所有能力安全降级：hasShell() 为 false，
 * speak() 返回 false，listen() 直接 reject，页面行为与没有本文件时一致。
 * 前端不要写平台判断，只认这一个契约。
 */

export interface ShellBridge {
  shellVersion(): string
  serverUrl(): string
  speak(text: string): void
  stopSpeaking(): void
  startListening(): boolean
  stopListening(): void
  callNumber(phone: string): void
  openUpdate(url: string): void
}

export type SpeakingState = 'start' | 'done'

declare global {
  interface Window {
    Shell?: ShellBridge
    onShellAsrResult?: (text: string) => void
    onShellAsrError?: (message: string) => void
    onShellSpeakState?: (state: SpeakingState) => void
  }
}

const ASR_TIMEOUT_MS = 60_000

interface PendingAsr {
  resolve: (text: string) => void
  reject: (reason: Error) => void
  timer: number
}

let pendingAsr: PendingAsr | null = null
let speaking = false
let speakSafetyTimer = 0
const speakingListeners = new Set<(state: SpeakingState) => void>()

function bridge(): ShellBridge | undefined {
  return typeof window === 'undefined' ? undefined : window.Shell
}

/** 是否运行在平板壳内。 */
export function hasShell(): boolean {
  return Boolean(bridge())
}

/** 壳版本号；网页端返回空串。 */
export function shellVersion(): string {
  try {
    return bridge()?.shellVersion() ?? ''
  } catch {
    return ''
  }
}

/** 当前服务端地址；网页端返回空串。 */
export function serverUrl(): string {
  try {
    return bridge()?.serverUrl() ?? ''
  } catch {
    return ''
  }
}

function settleAsr(text: string | null, error?: string) {
  const pending = pendingAsr
  if (!pending) return
  pendingAsr = null
  window.clearTimeout(pending.timer)
  if (text) {
    pending.resolve(text)
  } else {
    pending.reject(new Error(error || '没有听清，请再说一次'))
  }
}

function setSpeaking(next: boolean) {
  if (speaking === next) return
  speaking = next
  window.clearTimeout(speakSafetyTimer)
  if (next) {
    // TTS 引擎不可用时原生不会回调 done，兜底复位，避免按钮卡在「正在说」
    speakSafetyTimer = window.setTimeout(() => setSpeaking(false), 30_000)
  }
  const state: SpeakingState = next ? 'start' : 'done'
  speakingListeners.forEach((listener) => listener(state))
}

// 原生回调只装一次；网页端没有壳时永远不会被触发。
if (typeof window !== 'undefined') {
  window.onShellAsrResult = (text: string) => settleAsr(text)
  window.onShellAsrError = (message: string) => settleAsr(null, message)
  window.onShellSpeakState = (state: SpeakingState) => setSpeaking(state === 'start')
}

/** 开始播报。返回 false 表示当前没有壳，未播报。 */
export function speak(text: string): boolean {
  const shell = bridge()
  if (!shell || !text.trim()) return false
  try {
    shell.speak(text)
    setSpeaking(true)
    return true
  } catch {
    return false
  }
}

/** 停止播报（老人可以随时打断）。 */
export function stopSpeaking() {
  try {
    bridge()?.stopSpeaking()
  } finally {
    setSpeaking(false)
  }
}

export function isSpeaking(): boolean {
  return speaking
}

/** 订阅播报状态，返回取消订阅函数。 */
export function onSpeakingChange(listener: (state: SpeakingState) => void): () => void {
  speakingListeners.add(listener)
  return () => speakingListeners.delete(listener)
}

/**
 * 启动一次语音识别，返回识别文本。
 * 没有壳、壳不支持、用户取消、超时都会 reject，调用方负责提示。
 */
export function listen(): Promise<string> {
  const shell = bridge()
  if (!shell) return Promise.reject(new Error('当前不在平板壳内，无法语音输入'))

  settleAsr(null, '上一次识别还没结束')

  return new Promise<string>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      settleAsr(null, '等太久没听到声音，请再试一次')
      try {
        shell.stopListening()
      } catch {
        // 忽略：超时清理时壳可能已经结束识别
      }
    }, ASR_TIMEOUT_MS)
    pendingAsr = { resolve, reject, timer }

    try {
      const started = shell.startListening()
      if (!started) settleAsr(null, '这台平板暂时用不了语音识别')
    } catch {
      settleAsr(null, '语音识别没有启动成功')
    }
  })
}

/** 取消当前识别（识别中再次按话筒）。 */
export function stopListening() {
  try {
    bridge()?.stopListening()
  } finally {
    settleAsr(null, '已取消语音输入')
  }
}

/** 打开系统拨号盘（只带到号码，不直接拨出）。 */
export function callNumber(phone: string): boolean {
  const shell = bridge()
  if (!shell) return false
  try {
    shell.callNumber(phone)
    return true
  } catch {
    return false
  }
}

/** 打开壳的更新下载地址；网页端返回 false。 */
export function openUpdate(url: string): boolean {
  const shell = bridge()
  if (!shell) return false
  try {
    shell.openUpdate(url)
    return true
  } catch {
    return false
  }
}
