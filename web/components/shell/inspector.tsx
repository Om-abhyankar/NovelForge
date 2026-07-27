'use client'

import * as React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Target, Flame, Users, MapPin, GitBranch, History, Sparkles,
  ChevronRight, PanelRightClose, Timer,
} from 'lucide-react'

import { cn, formatNumber } from '@/lib/utils'
import { useStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import {
  Badge, Dot, ProgressBar, ProgressRing, Separator, Tooltip,
} from '@/components/ui/primitives'
import { SectionLabel } from '@/components/ui/card'

/** Tones cycle so each character gets a stable, distinct colour. */
const TONES = ['gold', 'indigo', 'success', 'warning', 'danger'] as const

export function Inspector({
  width,
  onResizeStart,
  onCollapse,
}: {
  width: number
  onResizeStart: (e: React.PointerEvent) => void
  onCollapse: () => void
}) {
  const {
    project, scene, entity, entitiesOf, analyse, notify, openExternal,
  } = useStore()

  const [findings, setFindings] = React.useState<string[]>([])
  const [checking, setChecking] = React.useState(false)

  const present = React.useMemo(() => {
    if (!scene) return []
    const ids = [...new Set([scene.povId, ...scene.characterIds].filter(Boolean))]
    return ids
      .map((id) => entity(id))
      .filter((e): e is NonNullable<typeof e> => Boolean(e))
  }, [entity, scene])

  const locations = React.useMemo(
    () =>
      (scene?.locationIds ?? [])
        .map((id) => entity(id))
        .filter((e): e is NonNullable<typeof e> => Boolean(e)),
    [entity, scene],
  )

  const threads = React.useMemo(() => {
    const all = entitiesOf('thread')
    const scenes = project?.chapters.flatMap((c) => c.scenes) ?? []
    return all.map((thread) => {
      const hits = scenes.filter((s) => s.threadIds.includes(thread.id))
      return {
        id: thread.id,
        name: thread.name,
        pct: scenes.length ? Math.round((hits.length / scenes.length) * 100) : 0,
        active: scene ? scene.threadIds.includes(thread.id) : false,
      }
    })
  }, [entitiesOf, project, scene])

  // Run the real offline checks against the current scene.
  const runCheck = React.useCallback(async () => {
    setChecking(true)
    const report = await analyse('scene')
    setChecking(false)
    if (!report) return
    setFindings(
      report.findings
        .filter((f) => f.severity !== 'note')
        .slice(0, 5)
        .map((f) => f.message),
    )
    if (!report.findings.some((f) => f.severity !== 'note')) {
      notify('Nothing flagged in this scene.', 'success')
    }
  }, [analyse, notify])

  return (
    <motion.aside
      initial={false}
      animate={{ width }}
      transition={{ type: 'spring', stiffness: 420, damping: 38 }}
      className="relative z-10 flex h-full shrink-0 flex-col
                 border-l border-line/[0.07] bg-surface"
    >
      {/* Drag handle. Four pixels wide, but the hit area is generous and the
          highlight only appears on hover so it stays invisible until wanted. */}
      <div
        onPointerDown={onResizeStart}
        className="group absolute inset-y-0 -left-1 z-30 w-2 cursor-col-resize"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize panel"
      >
        <div
          className="absolute inset-y-0 left-1 w-px bg-transparent
                     transition-colors duration-fast group-hover:bg-gold/50"
        />
      </div>

      <div className="flex h-titlebar shrink-0 items-center gap-2 px-3">
        <span className="text-2xs font-semibold uppercase tracking-[0.14em]
                         text-ink-4">
          Scene
        </span>
        <div className="flex-1" />
        <Tooltip content="Hide panel" side="left">
          <Button
            variant="quiet"
            size="icon-sm"
            onClick={onCollapse}
            aria-label="Hide panel"
          >
            <PanelRightClose />
          </Button>
        </Tooltip>
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-3 pb-4">
        {/* -- progress ---------------------------------------------- */}
        <section className="rounded-lg border border-line/[0.07] bg-card p-3.5
                            shadow-sm">
          <div className="flex items-center gap-3.5">
            <ProgressRing
              value={project?.progress.percent ?? 0}
              size={62}
              stroke={5}
              label={`${Math.round(project?.progress.percent ?? 0)}%`}
              sublabel="of book"
            />
            <div className="min-w-0 flex-1 space-y-2">
              <div>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-xl font-semibold tabular text-ink">
                    {formatNumber(project?.words ?? 0)}
                  </span>
                  <span className="text-xs text-ink-4">
                    / {formatNumber(project?.targets.total ?? 0)}
                  </span>
                </div>
                <p className="text-2xs text-ink-4">words written</p>
              </div>
              {project?.progress.streak ? (
                <div className="flex items-center gap-1.5">
                  <Flame className="size-3 text-warning" />
                  <span className="text-2xs text-ink-3">
                    <span className="font-semibold text-ink-2">
                      {project.progress.streak} day
                    </span>{' '}
                    streak
                  </span>
                </div>
              ) : null}
            </div>
          </div>

          <Separator className="my-3" />

          <div className="grid grid-cols-3 gap-2 text-center">
            {[
              {
                label: 'This scene',
                value: formatNumber(scene?.words ?? 0),
              },
              {
                label: 'Per day',
                value: formatNumber(project?.progress.average ?? 0),
              },
              {
                label: 'Left',
                value: formatNumber(project?.progress.remaining ?? 0),
              },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-sm font-semibold tabular text-ink-2">
                  {stat.value}
                </div>
                <div className="text-2xs text-ink-4">{stat.label}</div>
              </div>
            ))}
          </div>

          {project?.progress.daysLeft !== null &&
          project?.progress.daysLeft !== undefined ? (
            <p className="mt-2.5 text-2xs text-ink-4">
              {project.progress.daysLeft} days left · need{' '}
              {formatNumber(project.progress.requiredDaily ?? 0)} a day
              {project.progress.onTrack === false ? ' · behind' : ''}
            </p>
          ) : null}
        </section>

        {/* -- in this scene ------------------------------------------ */}
        {present.length ? (
          <Group title="In this scene" icon={Users}>
            <div className="space-y-1">
              {present.map((c, index) => {
                const tone = TONES[index % TONES.length]!
                const isPov = scene?.povId === c.id
                return (
                  <button
                    key={c.id}
                    onClick={() => {
                      if (c.fields && Object.keys(c.fields).length)
                        notify(`${c.name} — ${c.role || 'no role set'}`)
                    }}
                    className="group flex w-full items-center gap-2.5 rounded-md
                               p-1.5 text-left transition-colors duration-fast
                               hover:bg-ink/[0.05]"
                  >
                    <span
                      className={cn(
                        'grid size-7 shrink-0 place-items-center rounded-full',
                        'text-2xs font-semibold ring-1 ring-inset',
                        tone === 'gold' && 'bg-gold/12 text-gold ring-gold/25',
                        tone === 'danger' &&
                          'bg-danger/12 text-danger ring-danger/25',
                        tone === 'indigo' &&
                          'bg-indigo/12 text-indigo ring-indigo/25',
                        tone === 'success' &&
                          'bg-success/12 text-success ring-success/25',
                        tone === 'warning' &&
                          'bg-warning/12 text-warning ring-warning/25',
                      )}
                    >
                      {c.name
                        .split(' ')
                        .map((w) => w[0])
                        .join('')
                        .slice(0, 2)
                        .toUpperCase()}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-xs font-medium
                                       text-ink-2">
                        {c.name}
                      </span>
                      <span className="block truncate text-2xs text-ink-4">
                        {c.role || '—'}
                      </span>
                    </span>
                    {isPov ? <Badge variant="gold">POV</Badge> : null}
                    <ChevronRight
                      className="size-3 shrink-0 text-ink-4 opacity-0
                                 transition-opacity duration-fast
                                 group-hover:opacity-100"
                    />
                  </button>
                )
              })}
            </div>
          </Group>
        ) : null}

        {/* -- setting ------------------------------------------------- */}
        {locations.length ? (
          <Group title="Setting" icon={MapPin}>
            <div className="space-y-1.5">
              {locations.map((loc) => (
                <div
                  key={loc.id}
                  className="w-full rounded-md border border-line/[0.07]
                             bg-card p-2.5 text-left"
                >
                  <div className="text-xs font-medium text-ink-2">
                    {loc.name}
                  </div>
                  {loc.summary ? (
                    <p className="mt-0.5 text-2xs leading-relaxed text-ink-4">
                      {loc.summary}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          </Group>
        ) : null}

        {/* -- scene structure ----------------------------------------- */}
        {scene ? (
          <Group title="Structure" icon={Target}>
            <div className="space-y-1.5">
              {(scene.type === 'sequel'
                ? ([
                    ['Reaction', scene.reaction],
                    ['Dilemma', scene.dilemma],
                    ['Decision', scene.decision],
                  ] as const)
                : ([
                    ['Goal', scene.goal],
                    ['Conflict', scene.conflict],
                    ['Disaster', scene.disaster],
                  ] as const)
              ).map(([label, value]) => (
                <div key={label} className="text-2xs leading-relaxed">
                  <span className="font-semibold text-ink-3">{label}: </span>
                  <span className={value ? 'text-ink-3' : 'text-ink-4 italic'}>
                    {value || 'not set'}
                  </span>
                </div>
              ))}
              {scene.valueStart || scene.valueEnd ? (
                <div className="pt-1 text-2xs text-ink-4">
                  {scene.valueStart || '?'} → {scene.valueEnd || '?'}
                </div>
              ) : null}
            </div>
          </Group>
        ) : null}

        {/* -- threads -------------------------------------------------- */}
        {threads.length ? (
          <Group title="Plot threads" icon={GitBranch}>
            <div className="space-y-2.5">
              {threads.map((t, index) => {
                const tone = TONES[index % 3] as 'gold' | 'indigo' | 'success'
                return (
                  <div key={t.id} className={cn(!t.active && 'opacity-55')}>
                    <div className="mb-1 flex items-center gap-1.5">
                      <Dot
                        className={cn(
                          tone === 'gold' && 'bg-gold',
                          tone === 'indigo' && 'bg-indigo',
                          tone === 'success' && 'bg-success',
                        )}
                      />
                      <span className="min-w-0 flex-1 truncate text-2xs
                                       text-ink-3">
                        {t.name}
                      </span>
                      <span className="text-2xs tabular text-ink-4">
                        {t.pct}%
                      </span>
                    </div>
                    <ProgressBar value={t.pct} tone={tone} />
                  </div>
                )
              })}
            </div>
          </Group>
        ) : null}

        {/* -- offline analysis ----------------------------------------- */}
        <Group title="Analysis" icon={Sparkles} accent>
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            loading={checking}
            onClick={() => void runCheck()}
          >
            Check this scene
          </Button>
          {findings.length ? (
            <div className="mt-2 space-y-1.5">
              {findings.map((f) => (
                <div
                  key={f}
                  className="rounded-md border border-indigo/[0.16]
                             bg-indigo/[0.055] p-2 text-2xs leading-relaxed
                             text-ink-3"
                >
                  {f}
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-2 px-1 text-2xs leading-relaxed text-ink-4">
              Runs entirely on this machine. Nothing is uploaded.
            </p>
          )}
        </Group>
      </div>
    </motion.aside>
  )
}

function Group({
  title,
  icon: Icon,
  accent,
  children,
}: {
  title: string
  icon: React.ElementType
  accent?: boolean
  children: React.ReactNode
}) {
  return (
    <section>
      <div className="mb-1.5 flex items-center gap-1.5 px-1">
        <Icon
          className={cn('size-3', accent ? 'text-indigo' : 'text-ink-4')}
        />
        <SectionLabel className="px-0">{title}</SectionLabel>
      </div>
      {children}
    </section>
  )
}
