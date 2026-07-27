'use client'

import * as React from 'react'
import { TooltipProvider } from '@/components/ui/primitives'
import { Store } from '@/lib/store'

/** Must stay in step with the [data-theme] blocks in globals.css. */
export const THEMES = ['dark', 'midnight', 'amoled', 'sepia', 'light'] as const
export type Theme = (typeof THEMES)[number]

interface ThemeContextValue {
  theme: Theme
  setTheme: (theme: Theme) => void
}

const ThemeContext = React.createContext<ThemeContextValue>({
  theme: 'dark',
  setTheme: () => {},
})

export const useTheme = () => React.useContext(ThemeContext)

/**
 * Theme state lives on `document.documentElement` as a `data-theme` attribute,
 * which every token in globals.css keys off. React only mirrors it, so the
 * inline boot script in layout.tsx can set it before first paint without
 * fighting hydration.
 */
export function AppProviders({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>('dark')

  React.useEffect(() => {
    const stored = localStorage.getItem('nf-theme') as Theme | null
    // Validate rather than trust: a theme name left over from an older build
    // would otherwise set data-theme to something with no tokens behind it,
    // and every colour in the app would fall back to nothing.
    const theme = stored && THEMES.includes(stored) ? stored : 'dark'
    setThemeState(theme)
    document.documentElement.setAttribute('data-theme', theme)
  }, [])

  const setTheme = React.useCallback((next: Theme) => {
    setThemeState(next)
    document.documentElement.setAttribute('data-theme', next)
    try {
      localStorage.setItem('nf-theme', next)
    } catch {
      /* private mode - the theme just will not persist */
    }
  }, [])

  const value = React.useMemo(() => ({ theme, setTheme }), [theme, setTheme])

  return (
    <ThemeContext.Provider value={value}>
      <TooltipProvider delayDuration={400} skipDelayDuration={200}>
        {/* Store must wrap the app: without it every control had nothing to
            call, which is why they all appeared to do nothing. */}
        <Store>{children}</Store>
      </TooltipProvider>
    </ThemeContext.Provider>
  )
}
