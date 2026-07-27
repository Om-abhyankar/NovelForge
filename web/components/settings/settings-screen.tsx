'use client'

import * as React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Search, RotateCcw, Lock, ExternalLink, Folder, ChevronRight, Check,
} from 'lucide-react'

import { cn, formatNumber } from '@/lib/utils'
import {
  SETTINGS, DEFAULTS, ALL_SETTINGS, searchSettings,
  type Setting, type SettingCategory,
} from '@/lib/settings-schema'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import { useTheme, type Theme } from '@/components/app-providers'
import { Button } from '@/components/ui/button'
import {
  Badge, Input, Select, SelectContent, SelectItem, SelectTrigger,
  SelectValue, Separator, Slider, Switch, Tooltip,
} from '@/components/ui/primitives'

type Value = string | number | boolean

/* ==========================================================================
   Store
   ========================================================================== */

function useSettingsStore() {
  const [values, setValues] = React.useState<Record<string, Value>>(DEFAULTS)
  const [loaded, setLoaded] = React.useState(false)

  React.useEffect(() => {
    try {
      const raw = localStorage.getItem('nf-settings')
      if (raw) setValues({ ...DEFAULTS, ...JSON.parse(raw) })
    } catch {
      /* corrupt storage must never stop the app opening */
    }
    setLoaded(true)
  }, [])

  const set = React.useCallback((id: string, value: Value) => {
    setValues((prev) => {
      const next = { ...prev, [id]: value }
      try {
        localStorage.setItem('nf-settings', JSON.stringify(next))
      } catch {
        /* ignore */
      }
      return next
    })
  }, [])

  const resetAll = React.useCallback(() => {
    setValues(DEFAULTS)
    try {
      localStorage.removeItem('nf-settings')
    } catch {
      /* ignore */
    }
  }, [])

  const changedCount = React.useMemo(
    () => Object.keys(DEFAULTS).filter((k) => values[k] !== DEFAULTS[k]).length,
    [values],
  )

  return { values, set, resetAll, changedCount, loaded }
}

/* ==========================================================================
   Screen
   ========================================================================== */

const REPO = 'https://github.com/novelforge/novelforge'

export function SettingsScreen() {
  const { values, set, resetAll, changedCount } = useSettingsStore()
  const { setTheme } = useTheme()
  const store = useStore()
  const [active, setActive] = React.useState('general')
  const [query, setQuery] = React.useState('')
  const scrollRef = React.useRef<HTMLDivElement>(null)

  /**
   * Run an action row.
   *
   * Everything here does something real or says plainly that it does not.
   * A button that silently no-ops is the defect this whole pass was fixing.
   */
  const runAction = React.useCallback(
    (setting: Setting) => {
      const { id } = setting
      switch (id) {
        case 'backup.export':
        case 'privacy.exportAll':
          void store.backup()
          break

        case 'privacy.clearCache':
          try {
            localStorage.removeItem('nf-settings-cache')
            store.notify('Cached data cleared.', 'success')
          } catch {
            store.notify('Nothing cached to clear.')
          }
          break

        case 'privacy.clearRecent':
          void store.loadLibrary()
          store.notify('Recent list rebuilt from the folder.', 'success')
          break

        case 'perf.clearCaches':
          void store.refresh()
          store.notify('Re-reading documents from disk…')
          break

        case 'key.reset':
          for (const s of ALL_SETTINGS)
            if (s.kind === 'shortcut') set(s.id, s.default)
          store.notify('Shortcuts restored to defaults.', 'success')
          break

        case 'key.export': {
          const profile = Object.fromEntries(
            ALL_SETTINGS.filter((s) => s.kind === 'shortcut').map((s) => [
              s.id,
              values[s.id] ?? s.default,
            ]),
          )
          const blob = new Blob([JSON.stringify(profile, null, 2)], {
            type: 'application/json',
          })
          const url = URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          link.download = 'novelforge-shortcuts.json'
          link.click()
          URL.revokeObjectURL(url)
          store.notify('Shortcut profile saved.', 'success')
          break
        }

        case 'key.import': {
          const input = document.createElement('input')
          input.type = 'file'
          input.accept = '.json'
          input.onchange = async () => {
            const file = input.files?.[0]
            if (!file) return
            try {
              const parsed = JSON.parse(await file.text())
              let count = 0
              for (const [key, val] of Object.entries(parsed)) {
                if (key.startsWith('key.')) {
                  set(key, val as Value)
                  count++
                }
              }
              store.notify(`Imported ${count} shortcuts.`, 'success')
            } catch {
              store.notify('That file was not a shortcut profile.', 'error')
            }
          }
          input.click()
          break
        }

        case 'updates.checkNow':
          store.notify(
            'Update checking is off by default. Turn it on above to let the ' +
              'app ask GitHub for a newer release.',
          )
          break

        case 'updates.releaseNotes':
        case 'about.changelog':
          window.open(`${REPO}/releases`, '_blank', 'noopener')
          break
        case 'about.github':
          window.open(REPO, '_blank', 'noopener')
          break
        case 'about.docs':
          window.open(`${REPO}#readme`, '_blank', 'noopener')
          break
        case 'about.bug':
          window.open(`${REPO}/issues/new`, '_blank', 'noopener')
          break
        case 'about.feature':
          window.open(`${REPO}/discussions`, '_blank', 'noopener')
          break
        case 'about.donate':
          window.open(`${REPO}#support`, '_blank', 'noopener')
          break
        case 'about.libraries':
          store.notify(
            'python-docx, Pillow, React, Next.js, Radix, Framer Motion, ' +
              'Lucide, Tailwind — all permissively licensed.',
          )
          break

        default:
          store.notify(`“${setting.label}” is not connected yet.`, 'error')
      }
    },
    [set, store, values],
  )

  /** Shared by the sidebar button and any 'reset' action row. */
  const confirmReset = React.useCallback(() => {
    if (
      window.confirm(
        'Reset every setting to its original value?\n\n' +
          'Your novels, documents and backups are not affected.',
      )
    ) {
      resetAll()
      store.notify('Settings restored to defaults.', 'success')
    }
  }, [resetAll, store])

  const results = React.useMemo(() => searchSettings(query), [query])
  const category = SETTINGS.find((c) => c.id === active) ?? SETTINGS[0]!

  // Changing the theme setting must change the theme immediately, not on save.
  const handleChange = React.useCallback(
    (id: string, value: Value) => {
      set(id, value)
      if (id === 'appearance.theme') setTheme(value as Theme)
    },
    [set, setTheme],
  )

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 })
  }, [active])

  return (
    <div className="flex h-full min-h-0 bg-canvas">
      {/* -- categories --------------------------------------------- */}
      <nav
        className="flex w-60 shrink-0 flex-col border-r border-line/[0.07]
                   bg-surface"
      >
        <div className="p-3 pb-2">
          <h1 className="px-1 pb-2 text-lg font-semibold tracking-tight text-ink">
            Settings
          </h1>
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search settings"
            icon={<Search />}
            className="h-8 text-xs"
          />
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-2.5 pb-2">
          {SETTINGS.map((c) => (
            <CategoryRow
              key={c.id}
              category={c}
              active={active === c.id && !query}
              onSelect={() => {
                setQuery('')
                setActive(c.id)
              }}
            />
          ))}
        </div>

        <div className="border-t border-line/[0.07] p-2.5">
          {changedCount > 0 ? (
            <p className="mb-2 px-1 text-2xs text-ink-4">
              {changedCount} setting{changedCount === 1 ? '' : 's'} changed from
              default
            </p>
          ) : null}
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start text-ink-3"
            onClick={confirmReset}
          >
            <RotateCcw />
            Restore defaults
          </Button>
        </div>
      </nav>

      {/* -- panel --------------------------------------------------- */}
      <div ref={scrollRef} className="min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-8 py-8">
          {query ? (
            <SearchResults
              query={query}
              results={results}
              values={values}
              onChange={handleChange}
              onAction={runAction}
              onReset={confirmReset}
            />
          ) : (
            <motion.div
              key={category.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18 }}
            >
              <header className="mb-7">
                <h2 className="text-2xl font-semibold tracking-tight text-ink">
                  {category.label}
                </h2>
                <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-ink-3">
                  {category.blurb}
                </p>
              </header>

              <div className="space-y-9">
                {category.groups.map((group) => (
                  <section key={group.title}>
                    <div className="mb-3">
                      <h3 className="text-2xs font-semibold uppercase
                                     tracking-[0.14em] text-ink-4">
                        {group.title}
                      </h3>
                      {group.hint ? (
                        <p className="mt-1.5 max-w-xl text-xs leading-relaxed
                                      text-ink-4">
                          {group.hint}
                        </p>
                      ) : null}
                    </div>
                    <div
                      className="divide-y divide-line/[0.06] overflow-hidden
                                 rounded-lg border border-line/[0.07] bg-card
                                 shadow-sm"
                    >
                      {group.settings.map((setting) => (
                        <SettingRow
                          key={setting.id}
                          setting={setting}
                          value={values[setting.id] ?? setting.default}
                          onChange={(v) => handleChange(setting.id, v)}
                          onAction={runAction}
                          onReset={confirmReset}
                        />
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}

function CategoryRow({
  category,
  active,
  onSelect,
}: {
  category: SettingCategory
  active: boolean
  onSelect: () => void
}) {
  const Icon = category.icon
  return (
    <button
      onClick={onSelect}
      className={cn(
        'group relative flex h-8 w-full items-center gap-2.5 rounded-md px-2',
        'text-left transition-colors duration-fast',
        active ? 'text-ink' : 'text-ink-3 hover:bg-ink/[0.04] hover:text-ink-2',
      )}
    >
      {active ? (
        <motion.span
          layoutId="settings-active"
          className="absolute inset-0 -z-10 rounded-md bg-ink/[0.07]
                     ring-1 ring-inset ring-line/[0.08]"
          transition={{ type: 'spring', stiffness: 500, damping: 40 }}
        />
      ) : null}
      <Icon
        className={cn('size-4 shrink-0', active && 'text-gold')}
        strokeWidth={active ? 2.2 : 1.9}
      />
      <span className="flex-1 truncate text-sm font-medium">
        {category.label}
      </span>
    </button>
  )
}

function SearchResults({
  query,
  results,
  values,
  onChange,
  onAction,
  onReset,
}: {
  query: string
  results: ReturnType<typeof searchSettings>
  values: Record<string, Value>
  onChange: (id: string, value: Value) => void
  onAction: (setting: Setting) => void
  onReset: () => void
}) {
  if (!results.length) {
    return (
      <div className="py-20 text-center">
        <p className="text-md text-ink-3">
          Nothing matches “{query}”.
        </p>
        <p className="mt-1.5 text-sm text-ink-4">
          Try a word from the setting itself, like “font” or “backup”.
        </p>
      </div>
    )
  }
  return (
    <div>
      <header className="mb-6">
        <h2 className="text-2xl font-semibold tracking-tight text-ink">
          {results.length} result{results.length === 1 ? '' : 's'}
        </h2>
        <p className="mt-1.5 text-sm text-ink-3">for “{query}”</p>
      </header>
      <div
        className="divide-y divide-line/[0.06] overflow-hidden rounded-lg
                   border border-line/[0.07] bg-card shadow-sm"
      >
        {results.map((setting) => (
          <SettingRow
            key={setting.id}
            setting={setting}
            value={values[setting.id] ?? setting.default}
            onChange={(v) => onChange(setting.id, v)}
            onAction={onAction}
            onReset={onReset}
            breadcrumb={`${setting.categoryLabel} · ${setting.group}`}
          />
        ))}
      </div>
    </div>
  )
}

/* ==========================================================================
   One row
   ========================================================================== */

function SettingRow({
  setting,
  value,
  onChange,
  onAction,
  onReset,
  breadcrumb,
}: {
  setting: Setting
  value: Value
  onChange: (value: Value) => void
  onAction: (setting: Setting) => void
  onReset: () => void
  breadcrumb?: string
}) {
  const blocked = Boolean(setting.unavailable)

  return (
    <div
      className={cn(
        'flex items-start gap-6 px-4 py-3.5 transition-colors duration-fast',
        !blocked && 'hover:bg-ink/[0.015]',
        blocked && 'bg-ink/[0.012]',
      )}
    >
      <div className="min-w-0 flex-1">
        {breadcrumb ? (
          <p className="mb-0.5 text-2xs text-ink-4">{breadcrumb}</p>
        ) : null}
        <div className="flex items-center gap-2">
          <label
            className={cn(
              'text-sm font-medium',
              blocked ? 'text-ink-4' : 'text-ink-2',
            )}
          >
            {setting.label}
          </label>
          {blocked ? (
            <Badge variant="outline">
              <Lock />
              Not applicable
            </Badge>
          ) : null}
          {setting.danger ? <Badge variant="danger">Careful</Badge> : null}
        </div>

        {setting.hint ? (
          <p className="mt-1 max-w-xl text-xs leading-relaxed text-ink-4">
            {setting.hint}
          </p>
        ) : null}

        {/* The honest explanation, styled as information rather than error -
            this is a design decision of the app, not a failure. */}
        {setting.unavailable ? (
          <p
            className="mt-2 max-w-xl rounded-md border border-indigo/[0.16]
                       bg-indigo/[0.05] p-2.5 text-xs leading-relaxed
                       text-ink-3"
          >
            {setting.unavailable}
          </p>
        ) : null}

        {setting.note ? (
          <p className="mt-2 max-w-xl border-l-2 border-gold/30 pl-2.5
                        text-xs leading-relaxed text-ink-4">
            {setting.note}
          </p>
        ) : null}
      </div>

      <div className="flex shrink-0 items-center pt-0.5">
        <Control
          setting={setting}
          value={value}
          onChange={onChange}
          onAction={onAction}
          onReset={onReset}
        />
      </div>
    </div>
  )
}

function Control({
  setting,
  value,
  onChange,
  onAction,
  onReset,
}: {
  setting: Setting
  value: Value
  onChange: (value: Value) => void
  onAction: (setting: Setting) => void
  onReset: () => void
}) {
  const disabled = Boolean(setting.unavailable)
  const [capturing, setCapturing] = React.useState(false)

  /* A real key-capture rebind: press the combination you want. */
  React.useEffect(() => {
    if (!capturing) return
    const onKey = (e: KeyboardEvent) => {
      e.preventDefault()
      e.stopPropagation()
      if (e.key === 'Escape') {
        setCapturing(false)
        return
      }
      // Ignore a bare modifier - wait for the actual key.
      if (['Control', 'Shift', 'Alt', 'Meta'].includes(e.key)) return
      const parts: string[] = []
      if (e.ctrlKey || e.metaKey) parts.push('Ctrl')
      if (e.shiftKey) parts.push('Shift')
      if (e.altKey) parts.push('Alt')
      parts.push(e.key.length === 1 ? e.key.toUpperCase() : e.key)
      onChange(parts.join(' '))
      setCapturing(false)
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [capturing, onChange])

  switch (setting.kind) {
    case 'toggle':
      return (
        <Switch
          checked={Boolean(value)}
          onCheckedChange={onChange}
          disabled={disabled}
          aria-label={setting.label}
        />
      )

    case 'select':
      return (
        <Select
          value={String(value)}
          onValueChange={onChange}
          disabled={disabled}
        >
          <SelectTrigger className="w-52">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {setting.options?.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                <span className="flex items-baseline gap-2">
                  <span>{option.label}</span>
                  {option.hint ? (
                    <span className="text-2xs text-ink-4">{option.hint}</span>
                  ) : null}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )

    case 'slider':
      return (
        <div className="flex w-52 items-center gap-3">
          <Slider
            value={[Number(value)]}
            min={setting.min ?? 0}
            max={setting.max ?? 100}
            step={setting.step ?? 1}
            onValueChange={([v]) => onChange(v ?? 0)}
            disabled={disabled}
            aria-label={setting.label}
          />
          <span className="w-16 shrink-0 text-right text-xs tabular text-ink-3">
            {Number(value)}
            {setting.unit ?? ''}
          </span>
        </div>
      )

    case 'number':
      return (
        <Input
          type="number"
          value={String(value)}
          onChange={(e) => onChange(Number(e.target.value) || 0)}
          className="w-40"
          suffix={setting.unit}
          disabled={disabled}
        />
      )

    case 'text':
      return (
        <Input
          value={String(value)}
          onChange={(e) => onChange(e.target.value)}
          className="w-52"
          disabled={disabled}
        />
      )

    case 'folder':
      // Wider than the other controls and dir="rtl" so a long path shows its
      // END - the folder you are actually in - rather than clipping it off.
      return (
        <div className="flex w-80 items-center gap-1.5">
          <Input
            value={String(value)}
            onChange={(e) => onChange(e.target.value)}
            title={String(value)}
            dir="rtl"
            className="flex-1 truncate text-left font-mono text-2xs"
            disabled={disabled}
          />
          <Tooltip content="Browse">
            <Button
              variant="secondary"
              size="icon-sm"
              aria-label="Browse"
              disabled={disabled}
              onClick={async () => {
                // A web page cannot open a folder picker, so the engine shows
                // a real Windows one and hands the path back.
                try {
                  const result = await api.pickFolder(
                    String(value),
                    setting.label,
                  )
                  if (result.path) onChange(result.path)
                } catch {
                  /* reported by the store's error path */
                }
              }}
            >
              <Folder />
            </Button>
          </Tooltip>
        </div>
      )

    case 'color':
      return (
        <div className="flex items-center gap-2">
          {['#D4AF37', '#7C6CFF', '#5DD39E', '#FF5D73', '#6CA8FF'].map((c) => (
            <button
              key={c}
              onClick={() => onChange(c)}
              aria-label={`Accent ${c}`}
              className={cn(
                'size-6 rounded-full transition-transform duration-fast',
                'hover:scale-110 active:scale-95',
                'ring-offset-2 ring-offset-card',
                String(value) === c ? 'ring-2 ring-ink/40' : 'ring-0',
              )}
              style={{ backgroundColor: c }}
            >
              {String(value) === c ? (
                <Check className="mx-auto size-3 text-black/70" strokeWidth={3} />
              ) : null}
            </button>
          ))}
        </div>
      )

    case 'shortcut':
      return (
        <button
          onClick={() => setCapturing((v) => !v)}
          className={cn(
            'min-w-28 rounded-md border px-2.5 py-1 font-mono text-xs',
            'transition-colors duration-fast',
            capturing
              ? 'border-gold bg-gold/10 text-gold animate-breathe'
              : 'border-line/[0.1] bg-sunken text-ink-2 hover:border-gold/40',
          )}
          title="Click, then press the keys you want"
        >
          {capturing ? 'Press keys…' : String(value)}
        </button>
      )

    case 'action': {
      const isReset = setting.id.endsWith('.reset')
      const isLink = setting.id.startsWith('about.')
      return (
        <Button
          variant={setting.danger ? 'danger' : 'secondary'}
          size="sm"
          disabled={disabled}
          onClick={() => (isReset ? onReset() : onAction(setting))}
        >
          {isLink ? <ExternalLink /> : null}
          {isReset ? 'Reset' : isLink ? 'Open' : 'Run'}
        </Button>
      )
    }

    case 'info':
      return (
        <span className="max-w-64 text-right text-xs tabular text-ink-3">
          {String(value)}
        </span>
      )

    default:
      return null
  }
}
