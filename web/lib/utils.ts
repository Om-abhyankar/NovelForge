import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Merge class names, with later Tailwind utilities winning over earlier ones. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** 12345 -> "12,345" */
export function formatNumber(n: number): string {
  return new Intl.NumberFormat('en-GB').format(Math.round(n || 0))
}

/** 12345 -> "12.3k", for tight spaces like sidebar counts. */
export function compactNumber(n: number): string {
  if (Math.abs(n) < 1000) return String(Math.round(n))
  return new Intl.NumberFormat('en-GB', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(n)
}

/** Words to a human reading time at 250 wpm. */
export function readingTime(words: number): string {
  if (!words) return '0 min'
  const minutes = words / 250
  if (minutes < 60) return `${Math.max(1, Math.round(minutes))} min`
  const total = Math.round(minutes)
  return `${Math.floor(total / 60)}h ${String(total % 60).padStart(2, '0')}m`
}

/** "2 hours ago", "yesterday", "3 Mar". */
export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return 'never'
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return 'never'
  const seconds = Math.floor((Date.now() - then) / 1000)
  if (seconds < 45) return 'just now'
  if (seconds < 90) return 'a minute ago'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`
  const days = Math.floor(hours / 24)
  if (days === 1) return 'yesterday'
  if (days < 7) return `${days} days ago`
  return new Date(then).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
  })
}

/** Trailing-edge debounce, for autosave and live counters. */
export function debounce<T extends (...args: never[]) => void>(
  fn: T,
  ms: number,
): T & { cancel: () => void } {
  let timer: ReturnType<typeof setTimeout> | undefined
  const wrapped = ((...args: Parameters<T>) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => fn(...args), ms)
  }) as T & { cancel: () => void }
  wrapped.cancel = () => {
    if (timer) clearTimeout(timer)
    timer = undefined
  }
  return wrapped
}

/** Words the way writers and publishers count them. */
export function countWords(text: string): number {
  if (!text?.trim()) return 0
  return text.split(/\s+/).filter((t) => /[\p{L}\p{N}]/u.test(t)).length
}

/** Platform-correct shortcut label: ⌘K on Mac, Ctrl+K elsewhere. */
export function shortcut(keys: string): string {
  const mac =
    typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
  return mac ? keys.replace(/Ctrl/g, '⌘').replace(/Alt/g, '⌥') : keys
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}
