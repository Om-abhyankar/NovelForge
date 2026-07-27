/**
 * Static export.
 *
 * The whole point: `next build` emits plain HTML/CSS/JS into ../novelforge/web,
 * which the Python server hands out. Someone cloning the repo runs Python and
 * nothing else - no Node, no npm install, no build step. Node exists here only
 * for development.
 */
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  distDir: '.next',
  // Written straight into the Python package so it ships with it.
  // (next export writes to `out` by default; see the build script.)
  images: {
    // No Node image optimiser at runtime, so images must be unoptimised.
    unoptimized: true,
  },
  // Relative asset paths, because the app is served from a local origin whose
  // port can change if 4321 is taken.
  assetPrefix: '',
  trailingSlash: true,
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: false },
}

export default nextConfig
