'use client'

import * as React from 'react'
import { Command } from 'cmdk'
import * as DialogPrimitive from '@radix-ui/react-dialog'
import {
  FileText, Users, Globe2, Clock, Settings, Sparkles, Plus,
  Search, Play, Download, Save, Focus, Palette, BookOpen, Wand2,
  Timer, BarChart3,
  // Aliased: the unprefixed name would shadow JavaScript's Map constructor,
  // which is used below and fails to compile in a confusing way.
  Map as MapIcon,
  type LucideIcon,
} from 'lucide-react'

import { cn, shortcut } from '@/lib/utils'

interface Action {
  id: string
  label: string
  icon: LucideIcon
  group: string
  kbd?: string
  hint?: string
}

const ACTIONS: Action[] = [
  { id: 'new-scene', label: 'New scene', icon: Plus, group: 'Create', kbd: 'Ctrl N' },
  { id: 'new-chapter', label: 'New chapter', icon: BookOpen, group: 'Create' },
  { id: 'new-character', label: 'New character', icon: Users, group: 'Create' },
  { id: 'generate-map', label: 'Generate a world map', icon: Wand2, group: 'Create', hint: 'Procedural, seeded' },

  { id: 'go-manuscript', label: 'Manuscript', icon: FileText, group: 'Go to' },
  { id: 'go-characters', label: 'Characters', icon: Users, group: 'Go to' },
  { id: 'go-world', label: 'World bible', icon: Globe2, group: 'Go to' },
  { id: 'go-maps', label: 'Maps', icon: MapIcon, group: 'Go to' },
  { id: 'go-timeline', label: 'Timeline', icon: Clock, group: 'Go to' },

  { id: 'compile', label: 'Compile manuscript', icon: Download, group: 'Manuscript', kbd: 'F5' },
  { id: 'save', label: 'Save', icon: Save, group: 'Manuscript', kbd: 'Ctrl S' },
  { id: 'diagnose', label: 'Diagnose this scene', icon: BarChart3, group: 'Manuscript', kbd: 'F7' },

  { id: 'focus', label: 'Focus mode', icon: Focus, group: 'View', kbd: 'F11' },
  { id: 'zen', label: 'Zen mode', icon: Play, group: 'View', kbd: 'F12' },
  { id: 'theme', label: 'Change theme', icon: Palette, group: 'View' },
  { id: 'sprint', label: 'Start a sprint', icon: Timer, group: 'View', kbd: 'F6' },

  { id: 'assistant', label: 'Ask the assistant', icon: Sparkles, group: 'Assistant' },
  { id: 'settings', label: 'Settings', icon: Settings, group: 'Assistant', kbd: 'Ctrl ,' },
]

/**
 * Command palette.
 *
 * Deliberately the fastest thing in the app: it opens on Ctrl+K from anywhere,
 * filters as you type, and every row shows its shortcut so the palette teaches
 * the keyboard rather than replacing it.
 */
export function CommandPalette({
  open,
  onOpenChange,
  onRun,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onRun?: (id: string) => void
}) {
  const groups = React.useMemo(() => {
    const map = new Map<string, Action[]>()
    for (const a of ACTIONS) {
      const list = map.get(a.group) ?? []
      list.push(a)
      map.set(a.group, list)
    }
    return [...map.entries()]
  }, [])

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-[3px]
                     data-[state=open]:animate-fade-in"
        />
        <DialogPrimitive.Content
          className="fixed left-1/2 top-[18vh] z-50 w-[calc(100vw-3rem)]
                     max-w-[34rem] -translate-x-1/2
                     overflow-hidden rounded-xl glass shadow-xl
                     data-[state=open]:animate-scale-in"
          aria-label="Command palette"
        >
          <DialogPrimitive.Title className="sr-only">Commands</DialogPrimitive.Title>
          <Command
            loop
            className="[&_[cmdk-group-heading]]:px-3
                       [&_[cmdk-group-heading]]:py-1.5
                       [&_[cmdk-group-heading]]:text-2xs
                       [&_[cmdk-group-heading]]:font-semibold
                       [&_[cmdk-group-heading]]:uppercase
                       [&_[cmdk-group-heading]]:tracking-[0.14em]
                       [&_[cmdk-group-heading]]:text-ink-4"
          >
            <div className="flex items-center gap-2.5 border-b border-line/[0.08]
                            px-3.5">
              <Search className="size-4 shrink-0 text-ink-4" />
              <Command.Input
                autoFocus
                placeholder="Type a command or search…"
                className="h-12 w-full bg-transparent text-md text-ink
                           outline-none placeholder:text-ink-4"
              />
              <kbd
                className="shrink-0 rounded-[4px] border border-line/[0.1]
                           bg-ink/[0.04] px-1.5 py-0.5 font-mono text-2xs
                           text-ink-4"
              >
                esc
              </kbd>
            </div>

            <Command.List className="max-h-[22rem] overflow-y-auto p-1.5">
              <Command.Empty className="px-3 py-8 text-center text-sm text-ink-4">
                Nothing matches that.
              </Command.Empty>

              {groups.map(([group, actions]) => (
                <Command.Group key={group} heading={group}>
                  {actions.map((action) => {
                    const Icon = action.icon
                    return (
                      <Command.Item
                        key={action.id}
                        value={`${action.label} ${action.group}`}
                        onSelect={() => {
                          onRun?.(action.id)
                          onOpenChange(false)
                        }}
                        className={cn(
                          'group flex cursor-pointer items-center gap-2.5',
                          'rounded-md px-2.5 py-2 text-sm text-ink-2',
                          'transition-colors duration-fast',
                          'data-[selected=true]:bg-ink/[0.07]',
                          'data-[selected=true]:text-ink',
                        )}
                      >
                        <Icon
                          className="size-4 shrink-0 text-ink-4
                                     group-data-[selected=true]:text-gold"
                          strokeWidth={1.9}
                        />
                        <span className="flex-1 truncate">{action.label}</span>
                        {action.hint ? (
                          <span className="text-2xs text-ink-4">{action.hint}</span>
                        ) : null}
                        {action.kbd ? (
                          <kbd
                            className="shrink-0 rounded-[4px] border
                                       border-line/[0.1] bg-ink/[0.04] px-1
                                       py-px font-mono text-2xs text-ink-4"
                          >
                            {shortcut(action.kbd)}
                          </kbd>
                        ) : null}
                      </Command.Item>
                    )
                  })}
                </Command.Group>
              ))}
            </Command.List>
          </Command>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}
