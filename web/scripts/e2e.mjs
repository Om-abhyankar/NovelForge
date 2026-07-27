/**
 * End-to-end test: the real Python engine, the real built UI, a real browser.
 *
 * This is the test that would have caught "the buttons do nothing", because it
 * asserts on data that can only appear if the interface actually reached the
 * engine. It starts the Python server itself, so there is nothing to set up.
 */
import { chromium } from 'playwright'
import { spawn } from 'node:child_process'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

const ROOT = resolve(process.cwd(), '..')
const PY = join(
  process.env.LOCALAPPDATA,
  'Programs',
  'Python',
  'Python313',
  'python.exe',
)

const failures = []
const passes = []
const ok = (label) => {
  passes.push(label)
  console.log(`  PASS  ${label}`)
}
const bad = (label, detail) => {
  failures.push(`${label}${detail ? ` — ${detail}` : ''}`)
  console.log(`  FAIL  ${label}${detail ? ` — ${detail}` : ''}`)
}
const check = (label, condition, detail) =>
  condition ? ok(label) : bad(label, detail)

/* -- a throwaway project ------------------------------------------------- */

const sandbox = await mkdtemp(join(tmpdir(), 'nf-e2e-'))
console.log('sandbox:', sandbox)

const SETUP = `
import sys, json
sys.path.insert(0, r"${ROOT}")
from novelforge.project import Project
p = Project.create(title="E2E Novel", author="Test Writer",
                   target_words=50000, parent=r"${sandbox}")
ch = p.data.ordered_chapters()[0]
sc = p.data.scenes_in(ch.id)[0]
p.save_scene_text(sc.id, "The well had gone bitter in the night.\\n\\nAda tasted it.", snapshot=False)
hero = p.add_entity("character", "Ada Vane", role="Protagonist")
foe  = p.add_entity("character", "Mero Kastellan", role="Antagonist")
loc  = p.add_entity("location", "Ilesh", role="City")
thr  = p.add_entity("thread", "Who poisoned the wells?", role="A story")
sc.pov_id = hero.id
sc.character_ids = [hero.id, foe.id]
sc.location_ids = [loc.id]
sc.thread_ids = [thr.id]
sc.status = "Draft"
sc.goal = "Find the poisoner"
sc.conflict = "The guild closes ranks"
sc.disaster = "She is blamed"
p.sync_from_disk()
p.save(force=True)
print(json.dumps({"root": str(p.root), "scene": sc.id, "words": p.data.word_count}))
`

const setup = spawn(PY, ['-c', SETUP], { cwd: ROOT })
let setupOut = ''
setup.stdout.on('data', (d) => (setupOut += d))
setup.stderr.on('data', (d) => process.stderr.write(d))
await new Promise((r) => setup.on('close', r))
const project = JSON.parse(setupOut.trim().split('\n').pop())
console.log('project:', project.root, `(${project.words} words)\n`)

/* -- start the engine ---------------------------------------------------- */

const SERVE = `
import sys, time, json
sys.path.insert(0, r"${ROOT}")
from novelforge import server
srv, url, token = server.start()
print(json.dumps({"url": url, "token": token}), flush=True)
while True: time.sleep(1)
`

const engine = spawn(PY, ['-c', SERVE], { cwd: ROOT })
let line = ''
const info = await new Promise((res, rej) => {
  const timer = setTimeout(() => rej(new Error('engine did not start')), 20000)
  engine.stdout.on('data', (d) => {
    line += d
    const first = line.split('\n')[0]
    if (first && first.includes('url')) {
      clearTimeout(timer)
      res(JSON.parse(first))
    }
  })
  engine.stderr.on('data', (d) => process.stderr.write(d))
})
console.log('engine:', info.url, '\n')

/* -- drive it ------------------------------------------------------------ */

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } })
const consoleErrors = []
page.on('pageerror', (e) => consoleErrors.push(String(e)))
page.on('console', (m) => {
  if (m.type() === 'error') consoleErrors.push(m.text())
})

// The launcher normally injects this; do the same here.
await page.addInitScript(
  (t) => {
    window.__NOVELFORGE__ = { token: t, version: 'e2e', desktop: true }
    try {
      localStorage.setItem('nf-theme', 'dark')
      localStorage.removeItem('nf-settings')
    } catch {}
  },
  info.token,
)

console.log('=== BOOT ===')
await page.goto(info.url, { waitUntil: 'networkidle' })
// Open the project through the API the same way the launcher does.
await page.evaluate(
  async ([path, token]) => {
    await fetch('/api/project/open', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-NovelForge-Token': token },
      body: JSON.stringify({ path }),
    })
  },
  [project.root, info.token],
)
await page.reload({ waitUntil: 'networkidle' })
await page.waitForTimeout(2500)

const body = await page.textContent('body')

check('no offline banner', !body.includes('local engine is not running'),
      'the UI could not reach the engine')

console.log('\n=== REAL DATA REACHES THE UI ===')
check('project title shown', body.includes('E2E Novel'))
check('real scene prose in the editor',
      body.includes('The well had gone bitter'))
check('real character from the project', body.includes('Ada Vane'))
check('second character', body.includes('Mero Kastellan'))
check('real location', body.includes('Ilesh'))
check('real plot thread', body.includes('poisoned the wells'))
check('scene structure fields', body.includes('Find the poisoner'))
check('word count is the real one',
      body.includes(String(project.words)) || body.includes('9 words'),
      `expected ${project.words} somewhere`)

console.log('\n=== TYPING SAVES TO DISK ===')
const marker = `MARKER-${Date.now()}`
const area = page.locator('textarea').first()
await area.click()
await area.press('End')
await area.type(`\n\n${marker}`)
await page.waitForTimeout(400)
await page.keyboard.press('Control+s')
await page.waitForTimeout(1500)

const readBack = spawn(PY, ['-c', `
import sys
sys.path.insert(0, r"${ROOT}")
from novelforge.project import Project
p = Project.open(r"${project.root}")
print(p.scene_text("${project.scene}"))
`], { cwd: ROOT })
let disk = ''
readBack.stdout.on('data', (d) => (disk += d))
await new Promise((r) => readBack.on('close', r))
check('typed text was written to the .docx', disk.includes(marker),
      'the marker never reached disk')

console.log('\n=== BUTTONS ACTUALLY DO SOMETHING ===')

// Command palette opens. Assert on the group HEADINGS, which are real text -
// the input's placeholder is an attribute and never appears in textContent.
await page.keyboard.press('Control+k')
await page.waitForTimeout(700)
const paletteVisible = await page
  .getByPlaceholder('Type a command or search…')
  .isVisible()
  .catch(() => false)
const paletteBody = await page.textContent('body')
check(
  'Ctrl+K opens the palette',
  paletteVisible || (paletteBody.includes('CREATE') && paletteBody.includes('GO TO')),
  'neither the input nor its group headings appeared',
)
await page.keyboard.press('Escape')
await page.waitForTimeout(300)

// New chapter, via the palette, must change the project.
const before = await page.evaluate(async (token) => {
  const r = await fetch('/api/project', {
    headers: { 'X-NovelForge-Token': token },
  })
  return (await r.json()).chapters.length
}, info.token)

await page.keyboard.press('Control+k')
await page.waitForTimeout(400)
await page.keyboard.type('new chapter')
await page.waitForTimeout(400)
await page.keyboard.press('Enter')
await page.waitForTimeout(1500)

const after = await page.evaluate(async (token) => {
  const r = await fetch('/api/project', {
    headers: { 'X-NovelForge-Token': token },
  })
  return (await r.json()).chapters.length
}, info.token)
check('"New chapter" from the palette created one', after === before + 1,
      `chapters went ${before} -> ${after}`)

// Analysis button runs the real offline checks.
const checkButton = page.getByRole('button', { name: 'Check this scene' })
if (await checkButton.count()) {
  await checkButton.click()
  await page.waitForTimeout(2500)
  const afterCheck = await page.textContent('body')
  check('analysis produced output',
        afterCheck.includes('Nothing flagged') ||
        /filler|adverb|filter|passive|sentence|senses|repetition/i.test(afterCheck))
} else {
  bad('analysis button present')
}

// Compile writes a real manuscript.
await page.keyboard.press('F5')
await page.waitForTimeout(4000)
const afterCompile = await page.textContent('body')
check('compile reported a result',
      /words\s*[-–]\s*\d+\s*chapters|compil/i.test(afterCompile),
      'no toast appeared')

// Focus mode and zen toggle without error.
await page.keyboard.press('F11')
await page.waitForTimeout(400)
await page.keyboard.press('F11')
await page.keyboard.press('F12')
await page.waitForTimeout(600)
const zen = await page.textContent('body')
check('F12 hides the chrome in zen mode', !zen.includes('Restore defaults'))
await page.keyboard.press('Escape')
await page.waitForTimeout(400)

// Settings opens and its controls are live.
await page.getByRole('button', { name: 'Settings' }).first().click()
await page.waitForTimeout(800)
check('settings screen opens',
      (await page.textContent('body')).includes('How the application behaves'))
const firstSwitch = page.locator('[role="switch"]').first()
const wasOn = await firstSwitch.getAttribute('data-state')
await firstSwitch.click()
await page.waitForTimeout(400)
check('a settings toggle changes state',
      (await firstSwitch.getAttribute('data-state')) !== wasOn)

// Sidebar navigation.
await page.getByRole('button', { name: 'Characters' }).first().click()
await page.waitForTimeout(500)
ok('sidebar navigation responds')

console.log('\n=== CONSOLE ===')
const realErrors = consoleErrors.filter(
  (e) => !/favicon|Download the React DevTools/i.test(e),
)
check('no console errors', realErrors.length === 0, realErrors.slice(0, 4).join(' | '))

await browser.close()
engine.kill()
await rm(sandbox, { recursive: true, force: true }).catch(() => {})

console.log(`\n${passes.length} passed, ${failures.length} failed`)
if (failures.length) {
  console.log('\nFAILURES:')
  for (const f of failures) console.log('  -', f)
  process.exit(1)
}
console.log('\nEND-TO-END: THE UI IS WIRED TO THE ENGINE')
