'use client'

import * as React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  BookOpen, Users, Globe2, Map, Clock, StickyNote, FlaskConical,
  Sparkles, Settings, Search, ChevronRight, Pin, PanelLeftClose,
  PanelLeft, Feather, Moon, Sun, Coffee, Contrast, type LucideIcon,
} from 'lucide-react'

import { cn, compactNumber, shortcut } from '@/lib/utils'
import { useStore } from '@/lib/store'
import { useTheme, type Theme } from '@/components/app-providers'
import { Button } from '@/components/ui/button'
import { Tooltip } from '@/components/ui/primitives'

const THEME_ORDER: Theme[] = ['dark', 'midnight', 'amoled', 'sepia', 'light']
const THEME_ICON: Record<Theme, LucideIcon> = {
  dark: Moon,
  midnight: Moon,
  amoled: Contrast,
  sepia: Coffee,
  light: Sun,
}

export interface NavItem {
  id: string
  label: string
  icon: LucideIcon
  count?: number
  accent?: boolean
}

/**
 * Counts come from the open project, not from constants. They used to be
 * hardcoded, so the sidebar showed "42 scenes" on an empty novel.
 */
function useNavSections(): { heading: string | null; items: NavItem[] }[] {
  const { project, scenes, entitiesOf } = useStore()
  return React.useMemo(
    () => [
      {
        heading: null,
        items: [
          { id: 'manuscript', label: 'Manuscript', icon: BookOpen,
            count: scenes.length },
          { id: 'characters', label: 'Characters', icon: Users,
            count: entitiesOf('character').length },
          { id: 'world', label: 'World', icon: Globe2,
            count: entitiesOf('faction').length + entitiesOf('item').length },
          { id: 'maps', label: 'Maps', icon: Map },
          { id: 'timeline', label: 'Timeline', icon: Clock,
            count: project?.events.length ?? 0 },
        ],
      },
      {
        heading: 'Workspace',
        items: [
          { id: 'notes', label: 'Notes', icon: StickyNote,
            count: project?.notes.length ?? 0 },
          { id: 'threads', label: 'Plot threads', icon: FlaskConical,
            count: entitiesOf('thread').length },
          { id: 'analysis', label: 'Analysis', icon: Sparkles, accent: true },
        ],
      },
    ],
    [entitiesOf, project, scenes.length],
  )
}

export function Sidebar({
  collapsed,
  onToggle,
  active,
  onSelect,
  onOpenPalette,
}: {
  collapsed: boolean
  onToggle: () => void
  active: string
  onSelect: (id: string) => void
  onOpenPalette: () => void
}) {
  const { theme, setTheme } = useTheme()
  const ThemeIcon = THEME_ICON[theme] ?? Moon
  const cycleTheme = () =>
    setTheme(THEME_ORDER[(THEME_ORDER.indexOf(theme) + 1) % THEME_ORDER.length]!)

  const { project, scenes, sceneId, selectScene } = useStore()
  const sections = useNavSections()

  // "Recent" is the real scene list, most-recently-worked first. There is no
  // separate recents store to drift out of sync with the project.
  const recent = React.useMemo(
    () => scenes.filter((s) => s.words > 0).slice(-6).reverse(),
    [scenes],
  )
  const pinned = React.useMemo(
    () => (project?.entities ?? []).filter((e) => e.isPov).slice(0, 4),
    [project],
  )

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 60 : 272 }}
      transition={{ type: 'spring', stiffness: 420, damping: 38 }}
      className="relative z-20 flex h-full shrink-0 flex-col
                 border-r border-line/[0.07] bg-surface"
    >
      {/* -- identity ------------------------------------------------- */}
      <div
        className={cn(
          'flex h-titlebar shrink-0 items-center gap-2 px-3',
          collapsed && 'justify-center px-0',
        )}
      >
        <div
          className="grid size-7 shrink-0 place-items-center rounded-md
                     bg-gold-sheen text-canvas shadow-sm"
        >
          <Feather className="size-3.5" strokeWidth={2.5} />
        </div>
        {!collapsed && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="truncate text-sm font-semibold tracking-tight text-ink"
          >
            NovelForge
          </motion.span>
        )}
      </div>

      {/* -- search --------------------------------------------------- */}
      <div className={cn('px-2.5 pb-2', collapsed && 'px-2')}>
        {collapsed ? (
          <Tooltip content="Search" kbd={shortcut('Ctrl K')} side="right">
            <Button
              variant="quiet"
              size="icon-sm"
              className="mx-auto"
              onClick={onOpenPalette}
              aria-label="Search"
            >
              <Search />
            </Button>
          </Tooltip>
        ) : (
          <button
            onClick={onOpenPalette}
            className="group flex h-8 w-full items-center gap-2 rounded-md
                       border border-line/[0.07] bg-sunken px-2.5
                       text-left text-xs text-ink-4 shadow-sm
                       transition-colors duration-fast
                       hover:border-line/[0.14] hover:text-ink-3"
          >
            <Search className="size-3.5 shrink-0" />
            <span className="flex-1 truncate">Search or jump to…</span>
            <kbd
              className="rounded-[4px] border border-line/[0.1] bg-ink/[0.04]
                         px-1 py-px font-mono text-2xs text-ink-4"
            >
              {shortcut('Ctrl K')}
            </kbd>
          </button>
        )}
      </div>

      {/* -- navigation ------------------------------------------------ */}
      <nav className="min-h-0 flex-1 overflow-y-auto px-2.5 pb-2">
        {sections.map((section, index) => (
          <div key={section.heading ?? index} className={cn(index > 0 && 'mt-5')}>
            {section.heading && !collapsed ? (
              <div
                className="mb-1 px-2 text-2xs font-semibold uppercase
                           tracking-[0.14em] text-ink-4"
              >
                {section.heading}
              </div>
            ) : null}
            <div className="space-y-px">
              {section.items.map((item) => (
                <NavRow
                  key={item.id}
                  item={item}
                  collapsed={collapsed}
                  active={active === item.id}
                  onSelect={() => onSelect(item.id)}
                />
              ))}
            </div>
          </div>
        ))}

        <AnimatePresence initial={false}>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {pinned.length ? (
                <ListGroup title="Point of view" icon={Pin}>
                  {pinned.map((p) => (
                    <li key={p.id}>
                      <button
                        onClick={() => onSelect('characters')}
                        className="group flex w-full items-center gap-2 rounded-md
                                   px-2 py-1.5 text-left transition-colors
                                   duration-fast hover:bg-ink/[0.05]"
                      >
                        <span className="size-1 shrink-0 rounded-full bg-gold/70" />
                        <span className="min-w-0 flex-1 truncate text-xs text-ink-3
                                         group-hover:text-ink-2">
                          {p.name}
                        </span>
                      </button>
                    </li>
                  ))}
                </ListGroup>
              ) : null}

              {recent.length ? (
                <ListGroup title="Recent scenes" icon={Clock}>
                  {recent.map((r) => (
                    <li key={r.id}>
                      <button
                        onClick={() => void selectScene(r.id)}
                        className={cn(
                          'group flex w-full items-center gap-2 rounded-md',
                          'px-2 py-1.5 text-left transition-colors duration-fast',
                          'hover:bg-ink/[0.05]',
                          r.id === sceneId && 'bg-ink/[0.06]',
                        )}
                      >
                        <span
                          className={cn(
                            'min-w-0 flex-1 truncate text-xs',
                            r.id === sceneId
                              ? 'text-ink-2'
                              : 'text-ink-3 group-hover:text-ink-2',
                          )}
                        >
                          {r.title}
                        </span>
                        <span className="shrink-0 text-2xs tabular text-ink-4">
                          {compactNumber(r.words)}
                        </span>
                      </button>
                    </li>
                  ))}
                </ListGroup>
              ) : null}
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      {/* -- footer ----------------------------------------------------
          The theme control lives here rather than floating over the window.
          As an absolutely-positioned overlay it sat on top of this Settings
          button and swallowed its clicks. */}
      <div
        className={cn(
          'flex shrink-0 items-center gap-1 border-t border-line/[0.07] p-2',
          collapsed && 'flex-col',
        )}
      >
        <Tooltip content="Settings" side="right">
          <Button
            variant={active === 'settings' ? 'secondary' : 'quiet'}
            size="icon-sm"
            onClick={() => onSelect('settings')}
            aria-label="Settings"
          >
            <Settings />
          </Button>
        </Tooltip>
        <Tooltip content={`Theme: ${theme}`} side="right">
          <Button
            variant="quiet"
            size="icon-sm"
            onClick={cycleTheme}
            aria-label="Change theme"
          >
            <ThemeIcon />
          </Button>
        </Tooltip>
        {!collapsed && <div className="flex-1" />}
        <Tooltip
          content={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          side="right"
        >
          <Button
            variant="quiet"
            size="icon-sm"
            onClick={onToggle}
            aria-label="Toggle sidebar"
          >
            {collapsed ? <PanelLeft /> : <PanelLeftClose />}
          </Button>
        </Tooltip>
      </div>
    </motion.aside>
  )
}

/**
 * A navigation row.
 *
 * The active state uses a sliding indicator shared across rows via
 * `layoutId`, so selection glides between items instead of blinking - one of
 * the details that separates a considered UI from a styled one.
 */
function NavRow({
  item,
  collapsed,
  active,
  onSelect,
}: {
  item: NavItem
  collapsed: boolean
  active: boolean
  onSelect: () => void
}) {
  const Icon = item.icon
  const row = (
    <button
      onClick={onSelect}
      className={cn(
        'group relative flex h-8 w-full items-center gap-2.5 rounded-md px-2',
        'text-left transition-colors duration-fast',
        collapsed && 'justify-center px-0',
        active ? 'text-ink' : 'text-ink-3 hover:text-ink-2 hover:bg-ink/[0.04]',
      )}
      aria-current={active ? 'page' : undefined}
    >
      {active ? (
        <motion.span
          layoutId="nav-active"
          className="absolute inset-0 -z-10 rounded-md bg-ink/[0.07]
                     ring-1 ring-inset ring-line/[0.08]"
          transition={{ type: 'spring', stiffness: 500, damping: 40 }}
        />
      ) : null}
      <Icon
        className={cn(
          'size-4 shrink-0 transition-colors duration-fast',
          active && (item.accent ? 'text-indigo' : 'text-gold'),
        )}
        strokeWidth={active ? 2.2 : 1.9}
      />
      {!collapsed && (
        <>
          <span className="min-w-0 flex-1 truncate text-sm font-medium">
            {item.label}
          </span>
          {item.count !== undefined ? (
            <span className="shrink-0 text-2xs tabular text-ink-4">
              {compactNumber(item.count)}
            </span>
          ) : null}
          {item.accent ? (
            <span className="size-1.5 shrink-0 rounded-full bg-indigo
                             shadow-[0_0_8px_rgb(var(--indigo)/0.7)]" />
          ) : null}
        </>
      )}
    </button>
  )

  return collapsed ? (
    <Tooltip content={item.label} side="right">
      {row}
    </Tooltip>
  ) : (
    row
  )
}

function ListGroup({
  title,
  icon: Icon,
  children,
}: {
  title: string
  icon: LucideIcon
  children: React.ReactNode
}) {
  const [open, setOpen] = React.useState(true)
  return (
    <div className="mt-5">
      <button
        onClick={() => setOpen((v) => !v)}
        className="mb-0.5 flex w-full items-center gap-1.5 px-2 py-1
                   text-2xs font-semibold uppercase tracking-[0.14em]
                   text-ink-4 transition-colors duration-fast hover:text-ink-3"
      >
        <ChevronRight
          className={cn(
            'size-3 transition-transform duration-normal',
            open && 'rotate-90',
          )}
        />
        <Icon className="size-3" />
        <span className="flex-1 text-left">{title}</span>
      </button>
      <AnimatePresence initial={false}>
        {open ? (
          <motion.ul
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18, ease: [0.32, 0.72, 0, 1] }}
            className="overflow-hidden"
          >
            {children}
          </motion.ul>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
