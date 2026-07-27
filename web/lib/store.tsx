'use client'

import * as React from 'react'

import {
  api, ApiError, type AnalysisReport, type Chapter, type Entity,
  type LibraryEntry, type ProjectPayload, type Scene,
} from '@/lib/api'

/**
 * Application state.
 *
 * One provider holds the open project and the scene being edited. Components
 * read from here rather than from local mock arrays, which is what was missing
 * and why every control appeared to do nothing.
 *
 * `status` drives what the shell shows: 'connecting' during boot, 'offline' if
 * the engine is unreachable, 'empty' when no project is open, 'ready' otherwise.
 * A silent failure that renders an empty shell is worse than a visible message.
 */

export type Status = 'connecting' | 'offline' | 'empty' | 'ready'

export interface Toast {
  id: number
  message: string
  tone: 'info' | 'success' | 'error'
}

interface StoreValue {
  status: Status
  error: string
  project: ProjectPayload | null
  library: LibraryEntry[]
  libraryRoot: string

  sceneId: string
  sceneText: string
  sceneDirty: boolean
  sceneSaving: boolean

  toasts: Toast[]
  notify: (message: string, tone?: Toast['tone']) => void
  dismiss: (id: number) => void

  /* actions */
  refresh: () => Promise<void>
  loadLibrary: () => Promise<void>
  openProject: (path: string) => Promise<void>
  createProject: (title: string) => Promise<void>
  selectScene: (id: string) => Promise<void>
  setSceneText: (text: string) => void
  saveScene: (snapshot?: boolean) => Promise<void>
  updateScene: (id: string, changes: Partial<Scene>) => Promise<void>
  addScene: (chapterId: string, title?: string) => Promise<void>
  addChapter: (title?: string) => Promise<void>
  addEntity: (type: Entity['type'], name: string) => Promise<void>
  compile: () => Promise<void>
  backup: () => Promise<void>
  analyse: (scope: 'scene' | 'chapter' | 'book') => Promise<AnalysisReport | null>
  reveal: (path?: string) => Promise<void>
  openExternal: (path: string) => Promise<void>

  /* derived */
  scenes: Scene[]
  scene: Scene | null
  chapterOf: (sceneId: string) => Chapter | null
  entitiesOf: (type: Entity['type']) => Entity[]
  entity: (id: string) => Entity | null
}

const StoreContext = React.createContext<StoreValue | null>(null)

export function useStore(): StoreValue {
  const value = React.useContext(StoreContext)
  if (!value) throw new Error('useStore must be used inside <Store>')
  return value
}

const AUTOSAVE_MS = 30_000

export function Store({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = React.useState<Status>('connecting')
  const [error, setError] = React.useState('')
  const [project, setProject] = React.useState<ProjectPayload | null>(null)
  const [library, setLibrary] = React.useState<LibraryEntry[]>([])
  const [libraryRoot, setLibraryRoot] = React.useState('')

  const [sceneId, setSceneId] = React.useState('')
  const [sceneText, setSceneTextState] = React.useState('')
  const [sceneDirty, setSceneDirty] = React.useState(false)
  const [sceneSaving, setSceneSaving] = React.useState(false)

  const [toasts, setToasts] = React.useState<Toast[]>([])
  const toastId = React.useRef(0)

  // Held in refs so the autosave timer always sees current values without
  // being torn down and rebuilt on every keystroke.
  const dirtyRef = React.useRef(false)
  const textRef = React.useRef('')
  const idRef = React.useRef('')

  const notify = React.useCallback(
    (message: string, tone: Toast['tone'] = 'info') => {
      const id = ++toastId.current
      setToasts((t) => [...t, { id, message, tone }])
      window.setTimeout(
        () => setToasts((t) => t.filter((x) => x.id !== id)),
        tone === 'error' ? 9000 : 4500,
      )
    },
    [],
  )

  const dismiss = React.useCallback(
    (id: number) => setToasts((t) => t.filter((x) => x.id !== id)),
    [],
  )

  const fail = React.useCallback(
    (exc: unknown, fallback: string) => {
      const message = exc instanceof ApiError ? exc.message : fallback
      if (exc instanceof ApiError && exc.status === 0) setStatus('offline')
      setError(message)
      notify(message, 'error')
    },
    [notify],
  )

  /* -- loading ------------------------------------------------------- */

  const loadLibrary = React.useCallback(async () => {
    try {
      const result = await api.library()
      setLibrary(result.projects)
      setLibraryRoot(result.root)
    } catch (exc) {
      fail(exc, 'Could not read the project library.')
    }
  }, [fail])

  const applyProject = React.useCallback((payload: ProjectPayload) => {
    setProject(payload)
    setStatus('ready')
    setError('')
  }, [])

  const refresh = React.useCallback(async () => {
    try {
      const health = await api.health()
      if (!health.hasProject) {
        setStatus('empty')
        await loadLibrary()
        return
      }
      applyProject(await api.project())
      await loadLibrary()
    } catch (exc) {
      fail(exc, 'Could not reach the local engine.')
    }
  }, [applyProject, fail, loadLibrary])

  // Boot. The token is injected by the launcher after load, so give it a
  // moment before the first authenticated call.
  React.useEffect(() => {
    let cancelled = false
    const boot = async () => {
      for (let attempt = 0; attempt < 25 && !cancelled; attempt++) {
        if (typeof window !== 'undefined' && window.__NOVELFORGE__?.token) break
        await new Promise((r) => setTimeout(r, 120))
      }
      if (!cancelled) await refresh()
    }
    void boot()
    return () => {
      cancelled = true
    }
  }, [refresh])

  /* -- scenes -------------------------------------------------------- */

  const selectScene = React.useCallback(
    async (id: string) => {
      if (id === idRef.current) return
      // Flush the outgoing scene before switching, or its edits are lost.
      if (dirtyRef.current && idRef.current) {
        try {
          await api.saveScene(idRef.current, textRef.current, false)
        } catch {
          /* reported by the explicit save path */
        }
      }
      try {
        const result = await api.sceneText(id)
        idRef.current = id
        textRef.current = result.text
        dirtyRef.current = false
        setSceneId(id)
        setSceneTextState(result.text)
        setSceneDirty(false)
      } catch (exc) {
        fail(exc, 'Could not open that scene.')
      }
    },
    [fail],
  )

  const setSceneText = React.useCallback((text: string) => {
    textRef.current = text
    dirtyRef.current = true
    setSceneTextState(text)
    setSceneDirty(true)
  }, [])

  const saveScene = React.useCallback(
    async (snapshot = true) => {
      if (!idRef.current || !dirtyRef.current) return
      setSceneSaving(true)
      try {
        const result = await api.saveScene(
          idRef.current,
          textRef.current,
          snapshot,
        )
        dirtyRef.current = false
        setSceneDirty(false)
        setProject((prev) =>
          prev
            ? {
                ...prev,
                words: result.total,
                chapters: prev.chapters.map((c) => ({
                  ...c,
                  scenes: c.scenes.map((s) =>
                    s.id === result.id ? { ...s, words: result.words } : s,
                  ),
                })),
              }
            : prev,
        )
      } catch (exc) {
        fail(exc, 'Could not save this scene.')
      } finally {
        setSceneSaving(false)
      }
    },
    [fail],
  )

  // Debounced autosave on an interval rather than per keystroke.
  React.useEffect(() => {
    const timer = window.setInterval(() => {
      if (dirtyRef.current) void saveScene(false)
    }, AUTOSAVE_MS)
    return () => window.clearInterval(timer)
  }, [saveScene])

  // Last-chance save if the window goes away.
  React.useEffect(() => {
    const onHide = () => {
      if (dirtyRef.current && idRef.current) {
        void api.saveScene(idRef.current, textRef.current, false)
      }
    }
    window.addEventListener('beforeunload', onHide)
    return () => window.removeEventListener('beforeunload', onHide)
  }, [])

  /* -- mutations ----------------------------------------------------- */

  const openProject = React.useCallback(
    async (path: string) => {
      setStatus('connecting')
      try {
        applyProject(await api.openProject(path))
        idRef.current = ''
        setSceneId('')
        setSceneTextState('')
        notify('Opened.', 'success')
      } catch (exc) {
        fail(exc, 'Could not open that novel.')
      }
    },
    [applyProject, fail, notify],
  )

  const createProject = React.useCallback(
    async (title: string) => {
      try {
        applyProject(await api.createProject({ title }))
        notify(`Created “${title}”.`, 'success')
        await loadLibrary()
      } catch (exc) {
        fail(exc, 'Could not create that novel.')
      }
    },
    [applyProject, fail, loadLibrary, notify],
  )

  const updateScene = React.useCallback(
    async (id: string, changes: Partial<Scene>) => {
      try {
        applyProject(await api.updateScene(id, changes))
      } catch (exc) {
        fail(exc, 'Could not update that scene.')
      }
    },
    [applyProject, fail],
  )

  const addScene = React.useCallback(
    async (chapterId: string, title?: string) => {
      try {
        const result = await api.createScene(chapterId, title)
        applyProject(result)
        await selectScene(result.id)
        notify('Scene added.', 'success')
      } catch (exc) {
        fail(exc, 'Could not add a scene.')
      }
    },
    [applyProject, fail, notify, selectScene],
  )

  const addChapter = React.useCallback(
    async (title?: string) => {
      try {
        applyProject(await api.createChapter(title))
        notify('Chapter added.', 'success')
      } catch (exc) {
        fail(exc, 'Could not add a chapter.')
      }
    },
    [applyProject, fail, notify],
  )

  const addEntity = React.useCallback(
    async (type: Entity['type'], name: string) => {
      try {
        applyProject(await api.createEntity(type, name))
        notify(`Created a sheet for “${name}”.`, 'success')
      } catch (exc) {
        fail(exc, 'Could not create that sheet.')
      }
    },
    [applyProject, fail, notify],
  )

  const compile = React.useCallback(async () => {
    notify('Compiling…')
    try {
      const result = await api.compile()
      notify(result.summary, result.missing.length ? 'error' : 'success')
    } catch (exc) {
      fail(exc, 'Compile failed.')
    }
  }, [fail, notify])

  const backup = React.useCallback(async () => {
    notify('Backing up…')
    try {
      const result = await api.backup()
      notify(result.message, result.ok ? 'success' : 'error')
    } catch (exc) {
      fail(exc, 'Backup failed.')
    }
  }, [fail, notify])

  const analyse = React.useCallback(
    async (scope: 'scene' | 'chapter' | 'book') => {
      try {
        return await api.analyse(scope, scope === 'book' ? undefined : sceneId)
      } catch (exc) {
        fail(exc, 'Analysis failed.')
        return null
      }
    },
    [fail, sceneId],
  )

  const reveal = React.useCallback(
    async (path?: string) => {
      try {
        await api.reveal(path)
      } catch (exc) {
        fail(exc, 'Could not open that folder.')
      }
    },
    [fail],
  )

  const openExternal = React.useCallback(
    async (path: string) => {
      try {
        await api.openExternal(path)
      } catch (exc) {
        fail(exc, 'Could not open that document.')
      }
    },
    [fail],
  )

  /* -- derived ------------------------------------------------------- */

  const scenes = React.useMemo(
    () => project?.chapters.flatMap((c) => c.scenes) ?? [],
    [project],
  )
  const scene = React.useMemo(
    () => scenes.find((s) => s.id === sceneId) ?? null,
    [scenes, sceneId],
  )
  const chapterOf = React.useCallback(
    (id: string) =>
      project?.chapters.find((c) => c.scenes.some((s) => s.id === id)) ?? null,
    [project],
  )
  const entitiesOf = React.useCallback(
    (type: Entity['type']) =>
      project?.entities.filter((e) => e.type === type) ?? [],
    [project],
  )
  const entity = React.useCallback(
    (id: string) => project?.entities.find((e) => e.id === id) ?? null,
    [project],
  )

  // Open the first scene automatically, so a fresh launch lands on the page
  // rather than on an empty editor.
  React.useEffect(() => {
    if (status === 'ready' && !sceneId && scenes.length) {
      void selectScene(scenes[0]!.id)
    }
  }, [scenes, sceneId, selectScene, status])

  const value: StoreValue = {
    status, error, project, library, libraryRoot,
    sceneId, sceneText, sceneDirty, sceneSaving,
    toasts, notify, dismiss,
    refresh, loadLibrary, openProject, createProject,
    selectScene, setSceneText, saveScene, updateScene,
    addScene, addChapter, addEntity,
    compile, backup, analyse, reveal, openExternal,
    scenes, scene, chapterOf, entitiesOf, entity,
  }

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}
