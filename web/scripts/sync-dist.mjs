/**
 * Copy the static export into the Python package.
 *
 * This is the step that makes the project installable with Python alone.
 * `next build` writes to web/out; that output is copied to novelforge/web and
 * committed, so someone cloning the repo never needs Node or npm install.
 *
 * Run automatically as part of `npm run build`.
 */
import { cp, rm, mkdir, readdir, stat } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { join, resolve } from 'node:path'

const SOURCE = resolve(process.cwd(), 'out')
const TARGET = resolve(process.cwd(), '..', 'novelforge', 'web')

if (!existsSync(SOURCE)) {
  console.error(
    'No out/ directory. Run `next build` first — and check that\n' +
      "next.config.mjs still has output: 'export'.",
  )
  process.exit(1)
}

// Replace wholesale: a stale chunk left behind from a previous build is the
// classic cause of "it works in dev but the packaged app is broken".
await rm(TARGET, { recursive: true, force: true })
await mkdir(TARGET, { recursive: true })
await cp(SOURCE, TARGET, { recursive: true })

async function measure(dir) {
  let bytes = 0
  let files = 0
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) {
      const inner = await measure(full)
      bytes += inner.bytes
      files += inner.files
    } else {
      bytes += (await stat(full)).size
      files += 1
    }
  }
  return { bytes, files }
}

const { bytes, files } = await measure(TARGET)
console.log(
  `\nSynced UI → novelforge/web  (${files} files, ` +
    `${(bytes / 1024 / 1024).toFixed(1)} MB)`,
)
console.log('Commit this directory. It is what lets the app run without Node.')
