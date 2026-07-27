/**
 * The client for the local Python engine.
 *
 * Every call goes to the same origin the page was served from - the loopback
 * server started by novelforge/desktop.py. Nothing here ever contacts the
 * internet; there is no base URL to configure and no key to supply.
 *
 * The session token is injected into `window.__NOVELFORGE__` by the desktop
 * launcher after the page loads. It is regenerated every launch and never
 * stored, so another program on the machine cannot drive the API.
 */

export interface Scene {
  id: string
  title: string
  order: number
  synopsis: string
  status: string
  type: string
  words: number
  target: number
  include: boolean
  povId: string
  characterIds: string[]
  locationIds: string[]
  threadIds: string[]
  goal: string
  conflict: string
  disaster: string
  reaction: string
  dilemma: string
  decision: string
  valueStart: string
  valueEnd: string
  storyDate: string
  notes: string
}

export interface Chapter {
  id: string
  title: string
  order: number
  status: string
  include: boolean
  synopsis: string
  scenes: Scene[]
}

export interface Entity {
  id: string
  type: 'character' | 'location' | 'item' | 'faction' | 'thread'
  name: string
  role: string
  summary: string
  isPov: boolean
  aliases: string[]
  fields: Record<string, string>
}

export interface Beat {
  key: string
  name: string
  pct: number | null
  prompt: string
  answer: string
  done: boolean
  sceneIds: string[]
  targetWord: number | null
}

export interface TimelineEvent {
  id: string
  title: string
  when: string
  kind: string
  description: string
  onPage: boolean
}

export interface ProjectPayload {
  root: string
  title: string
  author: string
  genre: string
  logline: string
  structure: string
  words: number
  targets: { total: number; daily: number; deadline: string }
  progress: {
    percent: number
    remaining: number
    average: number
    daysLeft: number | null
    requiredDaily: number | null
    onTrack: boolean | null
    streak: number
    bestStreak: number
    sparkline: number[]
  }
  chapters: Chapter[]
  entities: Entity[]
  beats: Beat[]
  events: TimelineEvent[]
  notes: { id: string; title: string; kind: string }[]
}

export interface LibraryEntry {
  title: string
  path: string
  words: number
  target: number
  genre: string
  modified: string
  cover: string
}

export interface Finding {
  check: string
  severity: 'flag' | 'watch' | 'note'
  message: string
  examples: string[]
  count: number
}

export interface AnalysisReport {
  words: number
  sentences: number
  paragraphs: number
  metrics: Record<string, number>
  findings: Finding[]
}

declare global {
  interface Window {
    __NOVELFORGE__?: { token: string; version: string; desktop: boolean }
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** True when no Python engine is behind this page (e.g. `npm run dev`). */
export let offline = false

function token(): string {
  return typeof window !== 'undefined' ? (window.__NOVELFORGE__?.token ?? '') : ''
}

async function call<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const { method = 'GET', body } = options
  let response: Response
  try {
    response = await fetch(path, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-NovelForge-Token': token(),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: 'no-store',
    })
  } catch (cause) {
    // The engine is not running. Flag it once so the UI can say so plainly
    // instead of rendering an empty shell and looking broken.
    offline = true
    throw new ApiError(
      'The local engine is not running. Close and reopen NovelForge.',
      0,
    )
  }

  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      throw new ApiError(`Unreadable reply from ${path}`, response.status)
    }
  }

  if (!response.ok) {
    const message =
      (payload as { error?: string } | null)?.error ??
      `${method} ${path} failed (${response.status})`
    throw new ApiError(message, response.status)
  }

  offline = false
  return payload as T
}

const get = <T,>(path: string) => call<T>(path)
const post = <T,>(path: string, body?: unknown) =>
  call<T>(path, { method: 'POST', body })
const put = <T,>(path: string, body?: unknown) =>
  call<T>(path, { method: 'PUT', body })

export const api = {
  /* -- meta ---------------------------------------------------------- */
  health: () =>
    get<{ ok: boolean; version: string; hasProject: boolean }>('/api/health'),

  getSettings: () => get<Record<string, unknown>>('/api/settings'),
  saveSettings: (values: Record<string, unknown>) =>
    post<Record<string, unknown>>('/api/settings', { values }),

  /* -- library ------------------------------------------------------- */
  library: () =>
    get<{ projects: LibraryEntry[]; root: string }>('/api/library'),

  openProject: (path: string) =>
    post<ProjectPayload>('/api/project/open', { path }),

  createProject: (input: {
    title: string
    author?: string
    genre?: string
    structure?: string
    targetWords?: number
    dailyWords?: number
    deadline?: string
    packs?: string[]
  }) => post<ProjectPayload>('/api/project/create', input),

  project: () => get<ProjectPayload>('/api/project'),
  save: () => post<{ ok: boolean; words: number }>('/api/project/save'),
  sync: (force = false) =>
    post<ProjectPayload & { scenes: number; entities: number }>(
      '/api/project/sync',
      { force },
    ),

  /* -- writing ------------------------------------------------------- */
  sceneText: (id: string) =>
    post<{ id: string; text: string }>('/api/scene/text', { id }),

  saveScene: (id: string, text: string, snapshot = true) =>
    put<{ id: string; words: number; total: number }>('/api/scene/text', {
      id,
      text,
      snapshot,
    }),

  createScene: (chapterId: string, title?: string) =>
    post<ProjectPayload & { id: string }>('/api/scene/create', {
      chapterId,
      title,
    }),

  updateScene: (id: string, changes: Partial<Scene>) =>
    post<ProjectPayload>('/api/scene/update', { id, ...changes }),

  createChapter: (title?: string) =>
    post<ProjectPayload & { id: string }>('/api/chapter/create', { title }),

  createEntity: (type: Entity['type'], name: string, role?: string) =>
    post<ProjectPayload & { id: string }>('/api/entity/create', {
      type,
      name,
      role,
    }),

  /* -- tools --------------------------------------------------------- */
  analyse: (scope: 'scene' | 'chapter' | 'book', id?: string) =>
    post<AnalysisReport>('/api/analyse', { scope, id }),

  compile: (options?: {
    titlePage?: boolean
    runningHeader?: boolean
    toc?: boolean
    synopses?: boolean
  }) =>
    post<{
      path: string
      words: number
      chapters: number
      scenes: number
      skipped: string[]
      missing: string[]
      summary: string
    }>('/api/compile', options ?? {}),

  backup: () =>
    post<{ ok: boolean; path: string; message: string }>('/api/backup'),

  generateMap: (input: {
    seed?: string
    name?: string
    shape?: string
    climate?: string
    land?: number
  }) =>
    post<{
      name: string
      file: string
      png: string
      seed: string
      shapes: number
      pins: number
    }>('/api/map/generate', input),

  /* -- shell --------------------------------------------------------- */
  pickFolder: (initial?: string, title?: string) =>
    post<{ path: string }>('/api/pick-folder', { initial, title }),
  reveal: (path?: string) => post<{ ok: boolean }>('/api/reveal', { path }),
  openExternal: (path: string) =>
    post<{ ok: boolean }>('/api/open-external', { path }),
}
