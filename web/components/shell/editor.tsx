'use client'

import * as React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Bold, Italic, Quote, Heading2, List, Link2, Check, Cloud,
  Maximize2, AlignCenter, Type, Focus, FileText, Loader2,
} from 'lucide-react'

import { cn, formatNumber, readingTime } from '@/lib/utils'
import { useStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import {
  Tooltip, Separator, EmptyState, Skeleton,
} from '@/components/ui/primitives'

/**
 * The writing surface.
 *
 * Reads and writes the real scene through the store. It used to render a
 * hardcoded sample string, which is why typing changed nothing and every
 * toolbar button was inert.
 */
export function Editor({
  focusMode,
  typewriter,
  zen,
  onToggleFocus,
  onToggleZen,
  fontScale = 1,
}: {
  focusMode: boolean
  typewriter: boolean
  zen: boolean
  onToggleFocus: () => void
  onToggleZen: () => void
  fontScale?: number
}) {
  const {
    status, scene, sceneId, sceneText, sceneDirty, sceneSaving,
    setSceneText, saveScene, chapterOf, project, entity, addScene,
  } = useStore()

  const areaRef = React.useRef<HTMLTextAreaElement>(null)
  const [activeParagraph, setActiveParagraph] = React.useState(0)

  const words = React.useMemo(
    () => sceneText.split(/\s+/).filter((t) => /[\p{L}\p{N}]/u.test(t)).length,
    [sceneText],
  )

  const chapter = sceneId ? chapterOf(sceneId) : null
  const pov = scene?.povId ? entity(scene.povId) : null

  /* -- Ctrl+S, and formatting that wraps the selection ---------------- */

  const wrap = React.useCallback(
    (before: string, after = before) => {
      const area = areaRef.current
      if (!area) return
      const { selectionStart: start, selectionEnd: end, value } = area
      const selected = value.slice(start, end)
      const next =
        value.slice(0, start) + before + selected + after + value.slice(end)
      setSceneText(next)
      // Restore the selection around the wrapped text on the next paint.
      requestAnimationFrame(() => {
        area.focus()
        area.setSelectionRange(start + before.length, end + before.length)
      })
    },
    [setSceneText],
  )

  const insertAtLineStart = React.useCallback(
    (prefix: string) => {
      const area = areaRef.current
      if (!area) return
      const { selectionStart, value } = area
      const lineStart = value.lastIndexOf('\n', selectionStart - 1) + 1
      const next = value.slice(0, lineStart) + prefix + value.slice(lineStart)
      setSceneText(next)
      requestAnimationFrame(() => {
        area.focus()
        area.setSelectionRange(
          selectionStart + prefix.length,
          selectionStart + prefix.length,
        )
      })
    },
    [setSceneText],
  )

  const insertSceneBreak = React.useCallback(() => {
    const area = areaRef.current
    if (!area) return
    const { selectionStart, value } = area
    const next =
      value.slice(0, selectionStart) + '\n\n#\n\n' + value.slice(selectionStart)
    setSceneText(next)
    requestAnimationFrame(() => {
      area.focus()
      const at = selectionStart + 5
      area.setSelectionRange(at, at)
    })
  }, [setSceneText])

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return
      const key = e.key.toLowerCase()
      if (key === 's') {
        e.preventDefault()
        void saveScene(true)
      } else if (key === 'b' && document.activeElement === areaRef.current) {
        e.preventDefault()
        wrap('**')
      } else if (key === 'i' && document.activeElement === areaRef.current) {
        e.preventDefault()
        wrap('*')
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [saveScene, wrap])

  /* -- typewriter scrolling ------------------------------------------- */

  const keepCentred = React.useCallback(() => {
    const area = areaRef.current
    if (!area || !typewriter) return
    const before = area.value.slice(0, area.selectionStart)
    const line = before.split('\n').length
    const lineHeight = parseFloat(getComputedStyle(area).lineHeight) || 30
    const target = line * lineHeight - area.clientHeight / 2
    const parent = area.parentElement?.parentElement
    parent?.scrollTo({ top: Math.max(0, target), behavior: 'smooth' })
  }, [typewriter])

  /* -- states --------------------------------------------------------- */

  if (status === 'connecting') {
    return (
      <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-canvas">
        <div className="mx-auto w-full max-w-[42rem] space-y-4 px-8 pt-16">
          <Skeleton className="h-9 w-2/3" />
          <Skeleton className="h-4 w-1/3" />
          <div className="space-y-3 pt-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-4" style={{ width: `${70 + (i % 4) * 8}%` }} />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!scene) {
    return (
      <div className="flex min-h-0 min-w-0 flex-1 items-center justify-center bg-canvas">
        <EmptyState
          icon={<FileText />}
          title={project ? 'No scene selected' : 'No novel open'}
          description={
            project
              ? 'Pick a scene from the binder, or start a new one.'
              : 'Open or create a novel to begin writing.'
          }
          action={
            project && project.chapters[0] ? (
              <Button
                variant="primary"
                onClick={() => void addScene(project.chapters[0]!.id)}
              >
                New scene
              </Button>
            ) : null
          }
        />
      </div>
    )
  }

  const paragraphs = sceneText.split(/\n\n+/)

  return (
    <div className="relative flex min-h-0 min-w-0 flex-1 flex-col bg-canvas">
      <AnimatePresence>
        {!zen && (
          <motion.header
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex h-titlebar shrink-0 items-center gap-3 px-5"
          >
            <nav className="flex min-w-0 items-center gap-1.5 text-xs text-ink-4">
              <span className="truncate">{project?.title}</span>
              <span className="text-ink-4/50">/</span>
              <span className="truncate">{chapter?.title ?? '—'}</span>
              <span className="text-ink-4/50">/</span>
              <span className="truncate font-medium text-ink-2">
                {scene.title}
              </span>
            </nav>

            <div className="flex-1" />

            <div className="flex items-center gap-0.5">
              <Tooltip content="Focus mode" kbd="F11">
                <Button
                  variant={focusMode ? 'secondary' : 'quiet'}
                  size="icon-sm"
                  onClick={onToggleFocus}
                  aria-label="Focus mode"
                >
                  <Focus />
                </Button>
              </Tooltip>
              <Tooltip content="Typography — set in Settings › Writing Editor">
                <Button
                  variant="quiet"
                  size="icon-sm"
                  aria-label="Typography"
                  onClick={() =>
                    window.dispatchEvent(
                      new CustomEvent('nf:navigate', {
                        detail: { to: 'settings', category: 'editor' },
                      }),
                    )
                  }
                >
                  <Type />
                </Button>
              </Tooltip>
              <Tooltip content="Zen mode" kbd="F12">
                <Button
                  variant="quiet"
                  size="icon-sm"
                  onClick={onToggleZen}
                  aria-label="Zen mode"
                >
                  <Maximize2 />
                </Button>
              </Tooltip>
            </div>

            <Separator orientation="vertical" className="h-4" />
            <SaveIndicator dirty={sceneDirty} saving={sceneSaving} />
          </motion.header>
        )}
      </AnimatePresence>

      <div className={cn('relative min-h-0 flex-1 overflow-y-auto')}>
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-64
                     bg-gradient-to-b from-gold/[0.025] to-transparent"
        />

        <div
          className={cn(
            'relative mx-auto w-full px-8 pb-[45vh]',
            zen ? 'max-w-[46rem] pt-24' : 'max-w-[42rem] pt-10',
          )}
        >
          {!zen && (
            <div className="mb-8">
              <h1 className="font-serif text-3xl font-semibold text-ink">
                {scene.title}
              </h1>
              <p className="mt-2 text-sm text-ink-4">
                {[
                  scene.type === 'sequel' ? 'Sequel' : 'Scene',
                  pov?.name,
                  `${formatNumber(words)} words`,
                  readingTime(words),
                  scene.status,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </p>
            </div>
          )}

          {/*
            A textarea rather than a contenteditable: it is the only way to get
            reliable undo, spellcheck, IME input and selection behaviour for
            free. The styled paragraphs behind it provide the typography, and
            the textarea sits transparently on top.
          */}
          <div className="relative">
            <article
              aria-hidden
              className="prose-editor pointer-events-none select-none"
              style={{ fontSize: `${1.1875 * fontScale}rem` }}
            >
              {paragraphs.map((para, index) => {
                const isBreak = para.trim() === '#'
                return (
                  <p
                    key={index}
                    className={cn(
                      isBreak && 'scene-break',
                      focusMode &&
                        'transition-opacity duration-slow ' +
                          (activeParagraph === index
                            ? 'opacity-100'
                            : 'opacity-[0.28]'),
                    )}
                  >
                    {para || ' '}
                  </p>
                )
              })}
            </article>

            <textarea
              ref={areaRef}
              value={sceneText}
              onChange={(e) => setSceneText(e.target.value)}
              onKeyUp={keepCentred}
              onClick={(e) => {
                const area = e.currentTarget
                const before = area.value.slice(0, area.selectionStart)
                setActiveParagraph(before.split(/\n\n+/).length - 1)
              }}
              onBlur={() => void saveScene(false)}
              spellCheck
              className="prose-editor absolute inset-0 size-full resize-none
                         bg-transparent text-transparent caret-[rgb(var(--caret))]
                         outline-none selection:bg-[rgb(var(--selection)/0.3)]"
              style={{ fontSize: `${1.1875 * fontScale}rem` }}
              placeholder="Begin."
              aria-label={`Text of ${scene.title}`}
            />
          </div>
        </div>
      </div>

      <AnimatePresence>
        {!zen && (
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 400, damping: 32 }}
            className="pointer-events-none absolute inset-x-0 bottom-5
                       flex justify-center"
          >
            <div
              className="pointer-events-auto flex items-center gap-0.5
                         rounded-xl glass p-1 shadow-xl"
            >
              {/* Typed explicitly: an `as const` array whose members have
                  different keys becomes a union, and `kbd` then does not
                  exist on every branch. */}
              {(
                [
                  { icon: Bold, label: 'Bold', kbd: 'Ctrl B', run: () => wrap('**') },
                  { icon: Italic, label: 'Italic', kbd: 'Ctrl I', run: () => wrap('*') },
                  { icon: Heading2, label: 'Heading', run: () => insertAtLineStart('## ') },
                  { icon: Quote, label: 'Block quote', run: () => insertAtLineStart('> ') },
                  { icon: List, label: 'List', run: () => insertAtLineStart('- ') },
                  { icon: Link2, label: 'Link', run: () => wrap('[', '](url)') },
                ] satisfies {
                  icon: typeof Bold
                  label: string
                  kbd?: string
                  run: () => void
                }[]
              ).map(({ icon: Icon, label, kbd, run }) => (
                <Tooltip key={label} content={label} kbd={kbd}>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={label}
                    onClick={run}
                  >
                    <Icon />
                  </Button>
                </Tooltip>
              ))}
              <Separator orientation="vertical" className="mx-1 h-4" />
              <Tooltip content="Scene break">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Scene break"
                  onClick={insertSceneBreak}
                >
                  <AlignCenter />
                </Button>
              </Tooltip>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function SaveIndicator({
  dirty,
  saving,
}: {
  dirty: boolean
  saving: boolean
}) {
  const state = saving ? 'saving' : dirty ? 'unsaved' : 'saved'
  return (
    <div className="flex items-center gap-1.5 text-2xs text-ink-4">
      <span className="relative grid size-3.5 place-items-center">
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={state}
            initial={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.7 }}
            transition={{ duration: 0.14 }}
            className="absolute"
          >
            {state === 'saved' ? (
              <Check className="size-3.5 text-success" strokeWidth={2.5} />
            ) : state === 'saving' ? (
              <Loader2 className="size-3.5 animate-spin text-ink-4" />
            ) : (
              <Cloud className="size-3.5 animate-breathe text-warning" />
            )}
          </motion.span>
        </AnimatePresence>
      </span>
      <span className="tabular">
        {state === 'saved' ? 'Saved' : state === 'saving' ? 'Saving…' : 'Unsaved'}
      </span>
    </div>
  )
}
