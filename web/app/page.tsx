'use client'

import * as React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  BookOpen, Command, PanelRight, AlertTriangle, CheckCircle2, Info, X,
} from 'lucide-react'

import { cn, formatNumber, readingTime } from '@/lib/utils'
import { useStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Tooltip, Separator, Badge } from '@/components/ui/primitives'
import { Sidebar } from '@/components/shell/sidebar'
import { Editor } from '@/components/shell/editor'
import { Inspector } from '@/components/shell/inspector'
import { CommandPalette } from '@/components/shell/command-palette'
import { SettingsScreen } from '@/components/settings/settings-screen'

const INSPECTOR_MIN = 240
const INSPECTOR_MAX = 460

export default function Page() {
  const store = useStore()
  const [collapsed, setCollapsed] = React.useState(false)
  const [inspectorWidth, setInspectorWidth] = React.useState(320)
  const [inspectorOpen, setInspectorOpen] = React.useState(true)
  const [active, setActive] = React.useState('manuscript')
  const [paletteOpen, setPaletteOpen] = React.useState(false)
  const [focusMode, setFocusMode] = React.useState(false)
  const [zen, setZen] = React.useState(false)

  /* -- resizing the inspector ---------------------------------------- */
  const resizing = React.useRef(false)
  const onResizeStart = React.useCallback((e: React.PointerEvent) => {
    e.preventDefault()
    resizing.current = true
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    const move = (ev: PointerEvent) => {
      if (!resizing.current) return
      const next = window.innerWidth - ev.clientX
      setInspectorWidth(Math.min(INSPECTOR_MAX, Math.max(INSPECTOR_MIN, next)))
    }
    const up = () => {
      resizing.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
    }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
  }, [])

  /* -- commands, shared by the palette and the keyboard --------------- */
  const run = React.useCallback(
    (id: string) => {
      const first = store.project?.chapters[0]
      switch (id) {
        case 'new-scene':
          if (first) void store.addScene(first.id)
          else store.notify('Add a chapter first.', 'error')
          break
        case 'new-chapter':
          void store.addChapter()
          break
        case 'new-character': {
          const name = window.prompt('Character name')
          if (name?.trim()) void store.addEntity('character', name.trim())
          break
        }
        case 'generate-map':
          setActive('maps')
          store.notify('Map generation lives in the Maps section.')
          break
        case 'go-manuscript': setActive('manuscript'); break
        case 'go-characters': setActive('characters'); break
        case 'go-world': setActive('world'); break
        case 'go-maps': setActive('maps'); break
        case 'go-timeline': setActive('timeline'); break
        case 'compile': void store.compile(); break
        case 'save': void store.saveScene(true); break
        case 'backup': void store.backup(); break
        case 'diagnose':
          void store.analyse('scene').then((report) => {
            if (report) {
              const flags = report.findings.filter((f) => f.severity === 'flag')
              store.notify(
                flags.length
                  ? `${flags.length} thing${flags.length === 1 ? '' : 's'} worth fixing in ${formatNumber(report.words)} words.`
                  : `Nothing flagged in ${formatNumber(report.words)} words.`,
                flags.length ? 'info' : 'success',
              )
            }
          })
          break
        case 'focus': setFocusMode((v) => !v); break
        case 'zen': setZen((v) => !v); break
        case 'settings': setActive('settings'); break
        case 'reveal': void store.reveal(); break
        default:
          store.notify('That command is not connected yet.', 'error')
      }
    },
    [store],
  )

  /* -- keyboard ------------------------------------------------------- */
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey
      if (mod && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((v) => !v)
      } else if (e.key === 'F11') {
        e.preventDefault()
        setFocusMode((v) => !v)
      } else if (e.key === 'F12') {
        e.preventDefault()
        setZen((v) => !v)
      } else if (e.key === 'F5') {
        e.preventDefault()
        void store.compile()
      } else if (e.key === 'F7') {
        e.preventDefault()
        run('diagnose')
      } else if (mod && e.key === '\\') {
        e.preventDefault()
        setCollapsed((v) => !v)
      } else if (mod && e.key === ',') {
        e.preventDefault()
        setActive('settings')
      } else if (mod && e.key.toLowerCase() === 'b') {
        // Only Ctrl+Shift+B backs up; plain Ctrl+B is bold in the editor.
        if (e.shiftKey) {
          e.preventDefault()
          void store.backup()
        }
      } else if (e.key === 'Escape' && zen) {
        setZen(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [run, store, zen])

  // The editor's Typography button asks to jump to settings.
  React.useEffect(() => {
    const onNavigate = (e: Event) => {
      const detail = (e as CustomEvent<{ to?: string }>).detail
      if (detail?.to) setActive(detail.to)
    }
    window.addEventListener('nf:navigate', onNavigate)
    return () => window.removeEventListener('nf:navigate', onNavigate)
  }, [])

  const showSettings = active === 'settings'

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-canvas text-ink">
      <AnimatePresence initial={false}>
        {!zen && (
          <motion.div
            initial={{ marginLeft: 0 }}
            exit={{ marginLeft: -300 }}
            animate={{ marginLeft: 0 }}
            transition={{ type: 'spring', stiffness: 400, damping: 38 }}
            className="h-full"
          >
            <Sidebar
              collapsed={collapsed}
              onToggle={() => setCollapsed((v) => !v)}
              active={active}
              onSelect={setActive}
              onOpenPalette={() => setPaletteOpen(true)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <main className="flex min-w-0 flex-1 flex-col">
        <OfflineBanner />
        {showSettings ? (
          <SettingsScreen />
        ) : (
          <>
            <Editor
              focusMode={focusMode}
              typewriter
              zen={zen}
              onToggleFocus={() => setFocusMode((v) => !v)}
              onToggleZen={() => setZen((v) => !v)}
            />
            <AnimatePresence>{!zen && <StatusBar />}</AnimatePresence>
          </>
        )}
      </main>

      <AnimatePresence initial={false}>
        {inspectorOpen && !zen && !showSettings ? (
          <Inspector
            width={inspectorWidth}
            onResizeStart={onResizeStart}
            onCollapse={() => setInspectorOpen(false)}
          />
        ) : null}
      </AnimatePresence>

      {!inspectorOpen && !zen && !showSettings ? (
        <div className="absolute right-3 top-3 z-30">
          <Tooltip content="Show panel" side="left">
            <Button
              variant="secondary"
              size="icon-sm"
              onClick={() => setInspectorOpen(true)}
              aria-label="Show panel"
            >
              <PanelRight />
            </Button>
          </Tooltip>
        </div>
      ) : null}

      <CommandPalette
        open={paletteOpen}
        onOpenChange={setPaletteOpen}
        onRun={run}
      />
      <Toasts />
    </div>
  )
}

/** Shown when the Python engine cannot be reached. Never fail silently. */
function OfflineBanner() {
  const { status, error } = useStore()
  if (status !== 'offline') return null
  return (
    <div
      className="flex shrink-0 items-center gap-2 border-b border-danger/25
                 bg-danger/10 px-4 py-2 text-xs text-ink-2"
      role="alert"
    >
      <AlertTriangle className="size-3.5 shrink-0 text-danger" />
      <span className="flex-1">
        {error || 'The local engine is not running.'} Nothing you type here can
        be saved until it is back.
      </span>
      <Button
        variant="outline"
        size="xs"
        onClick={() => window.location.reload()}
      >
        Retry
      </Button>
    </div>
  )
}

function StatusBar() {
  const { project, scene, chapterOf, sceneId, reveal } = useStore()
  const words = project?.words ?? 0
  const chapter = sceneId ? chapterOf(sceneId) : null

  return (
    <motion.footer
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="flex h-statusbar shrink-0 items-center gap-3 border-t
                 border-line/[0.07] bg-surface px-4 text-2xs text-ink-4"
    >
      <button
        onClick={() => void reveal()}
        className="flex items-center gap-1.5 transition-colors duration-fast
                   hover:text-ink-3"
        title="Show this novel's folder"
      >
        <BookOpen className="size-3" />
        {project?.title ?? 'No novel open'}
      </button>
      <Separator orientation="vertical" className="h-3" />
      <span className="tabular">{formatNumber(words)} words</span>
      <Separator orientation="vertical" className="h-3" />
      <span className="tabular">{readingTime(words)}</span>
      {project?.targets.total ? (
        <>
          <Separator orientation="vertical" className="h-3" />
          <span className="tabular">
            {project.progress.percent.toFixed(1)}% of{' '}
            {formatNumber(project.targets.total)}
          </span>
        </>
      ) : null}
      {scene ? (
        <>
          <Separator orientation="vertical" className="h-3" />
          <Badge variant="gold">{scene.status}</Badge>
        </>
      ) : null}

      <div className="flex-1" />

      {project?.progress.streak ? (
        <>
          <span className="tabular">{project.progress.streak} day streak</span>
          <Separator orientation="vertical" className="h-3" />
        </>
      ) : null}
      {chapter && scene ? (
        <>
          <span className="truncate tabular">
            {chapter.title} · {scene.title}
          </span>
          <Separator orientation="vertical" className="h-3" />
        </>
      ) : null}
      <span className="flex items-center gap-1">
        <Command className="size-3" />
        Ctrl K
      </span>
    </motion.footer>
  )
}

function Toasts() {
  const { toasts, dismiss } = useStore()
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex
                    w-80 flex-col gap-2">
      <AnimatePresence initial={false}>
        {toasts.map((toast) => {
          const Icon =
            toast.tone === 'error'
              ? AlertTriangle
              : toast.tone === 'success'
                ? CheckCircle2
                : Info
          return (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, y: 12, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, x: 24, scale: 0.96 }}
              transition={{ type: 'spring', stiffness: 420, damping: 34 }}
              className={cn(
                'pointer-events-auto flex items-start gap-2.5 rounded-lg',
                'glass p-3 shadow-xl',
                toast.tone === 'error' && 'border-danger/25',
                toast.tone === 'success' && 'border-success/25',
              )}
              role="status"
            >
              <Icon
                className={cn(
                  'mt-px size-3.5 shrink-0',
                  toast.tone === 'error' && 'text-danger',
                  toast.tone === 'success' && 'text-success',
                  toast.tone === 'info' && 'text-ink-3',
                )}
              />
              <span className="flex-1 text-xs leading-relaxed text-ink-2">
                {toast.message}
              </span>
              <button
                onClick={() => dismiss(toast.id)}
                className="shrink-0 rounded p-0.5 text-ink-4 transition-colors
                           duration-fast hover:text-ink-2"
                aria-label="Dismiss"
              >
                <X className="size-3" />
              </button>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
