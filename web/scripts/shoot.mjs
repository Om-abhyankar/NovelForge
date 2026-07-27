/**
 * Screenshot the built UI so the design can be looked at rather than imagined.
 * Serves the static export over http (file:// breaks Next's asset paths) and
 * captures each theme plus the key screens. Also reports any console error or
 * page exception, which is how a silently broken screen gets caught.
 */
import { chromium } from 'playwright'
import { createServer } from 'node:http'
import { readFile, mkdir } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { extname, join, resolve } from 'node:path'

const ROOT = resolve(process.cwd(), 'out')
const OUT = resolve(process.env.TEMP, 'nf_shots')
await mkdir(OUT, { recursive: true })

const TYPES = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.woff2': 'font/woff2', '.woff': 'font/woff',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon',
  '.txt': 'text/plain',
}

const server = createServer(async (req, res) => {
  try {
    let p = decodeURIComponent((req.url || '/').split('?')[0])
    if (p.endsWith('/')) p += 'index.html'
    let file = join(ROOT, p)
    if (!existsSync(file)) file = join(ROOT, 'index.html')
    const body = await readFile(file)
    res.writeHead(200, {
      'Content-Type': TYPES[extname(file)] || 'application/octet-stream',
    })
    res.end(body)
  } catch {
    res.writeHead(404)
    res.end('not found')
  }
})

await new Promise((r) => server.listen(4399, r))
console.log('serving', ROOT, 'on :4399')

const browser = await chromium.launch()
const shots = []
const problems = []

async function open(theme) {
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1000 },
    deviceScaleFactor: 2,
  })
  page.on('pageerror', (e) => problems.push(`[${theme}] ${e}`))
  page.on('console', (m) => {
    if (m.type() === 'error') problems.push(`[${theme}] console: ${m.text()}`)
  })
  await page.addInitScript((t) => {
    try {
      localStorage.setItem('nf-theme', t)
      localStorage.removeItem('nf-settings')
    } catch {}
  }, theme)
  await page.goto('http://127.0.0.1:4399/', { waitUntil: 'networkidle' })
  await page.waitForTimeout(1200)
  return page
}

async function shoot(page, name) {
  const file = join(OUT, `${name}.png`)
  await page.screenshot({ path: file })
  shots.push(name)
  console.log('  shot', name)
}

for (const theme of ['dark', 'midnight', 'amoled', 'sepia', 'light']) {
  console.log(theme)
  const page = await open(theme)
  await shoot(page, `shell-${theme}`)

  // Settings on every theme: it is the densest screen and the most likely to
  // reveal a contrast or spacing failure.
  await page.getByRole('button', { name: 'Settings' }).first().click()
  await page.waitForTimeout(700)
  await shoot(page, `settings-${theme}`)

  if (theme === 'dark') {
    // A category with "not applicable" rows, to check that treatment reads as
    // information rather than as an error.
    await page.getByRole('button', { name: 'Privacy & Security' }).click()
    await page.waitForTimeout(500)
    await shoot(page, 'settings-privacy')

    await page.getByRole('button', { name: 'Manuscript Analysis' }).click()
    await page.waitForTimeout(500)
    await shoot(page, 'settings-analysis')

    await page.getByPlaceholder('Search settings').fill('font')
    await page.waitForTimeout(500)
    await shoot(page, 'settings-search')
  }
  await page.close()
}

await browser.close()
server.close()

console.log('\nDONE —', shots.length, 'shots in', OUT)
if (problems.length) {
  console.log('\nPAGE PROBLEMS:')
  for (const p of [...new Set(problems)]) console.log(' ', p)
} else {
  console.log('no console errors or page exceptions')
}
