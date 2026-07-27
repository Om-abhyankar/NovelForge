import type { Metadata, Viewport } from 'next'
import { Inter, Literata, JetBrains_Mono } from 'next/font/google'

import './globals.css'
import { AppProviders } from '@/components/app-providers'

/**
 * Fonts are fetched at build time and self-hosted into the static export, so
 * the shipped app never touches the network. Inter for UI, Literata for prose
 * (it was designed for long-form reading on screen), JetBrains Mono for code
 * and numbers.
 */
const sans = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
  adjustFontFallback: true,
})

const serif = Literata({
  subsets: ['latin'],
  variable: '--font-serif',
  display: 'swap',
  weight: ['400', '500', '600'],
  style: ['normal', 'italic'],
})

const mono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
  weight: ['400', '500'],
})

export const metadata: Metadata = {
  title: 'NovelForge',
  description: 'A writing studio for authors. Local, private, yours.',
  applicationName: 'NovelForge',
}

export const viewport: Viewport = {
  themeColor: '#0D1117',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html
      lang="en"
      data-theme="dark"
      suppressHydrationWarning
      className={`${sans.variable} ${serif.variable} ${mono.variable}`}
    >
      <head>
        {/*
          Applied before first paint so a reload never flashes the wrong theme.
          Inline because it must run before React hydrates.
        */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
(function () {
  try {
    var t = localStorage.getItem('nf-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', t);
  } catch (e) {}
})();`,
          }}
        />
      </head>
      <body className="font-sans antialiased">
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  )
}
