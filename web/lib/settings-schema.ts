import {
  Settings2, Palette, Type, Save, Microscope, FolderTree, Target,
  Bell, Keyboard, Download, Shield, Gauge, RefreshCw, Info,
  type LucideIcon,
} from 'lucide-react'

/**
 * The settings registry.
 *
 * Every preference in the app is declared here as data and rendered
 * generically. Hand-writing two hundred controls guarantees they drift apart
 * in spacing, wording and behaviour; declaring them means search, keyboard
 * navigation, reset-to-default and persistence are all written once.
 *
 * `unavailable` is deliberate and important. This app is offline and has no
 * accounts, so several settings people expect simply cannot be honest here.
 * Rather than shipping a switch that does nothing, the control renders
 * disabled with the reason visible. A dead toggle is worse than an absent one.
 */

export type SettingKind =
  | 'toggle' | 'select' | 'slider' | 'text' | 'number'
  | 'color' | 'action' | 'info' | 'folder' | 'shortcut'

export interface SelectOption {
  value: string
  label: string
  hint?: string
}

export interface Setting {
  id: string
  label: string
  hint?: string
  kind: SettingKind
  default: string | number | boolean
  options?: SelectOption[]
  min?: number
  max?: number
  step?: number
  unit?: string
  /** Inline explanatory note under the control. */
  note?: string
  /** Renders disabled with this reason. For things that cannot work offline. */
  unavailable?: string
  /** Destructive - styled as such and confirmed before running. */
  danger?: boolean
  /** Extra words the search box should match. */
  keywords?: string
}

export interface SettingGroup {
  title: string
  hint?: string
  settings: Setting[]
}

export interface SettingCategory {
  id: string
  label: string
  icon: LucideIcon
  blurb: string
  groups: SettingGroup[]
}

const onOff = (label: string, hint?: string, def = true): Partial<Setting> => ({
  kind: 'toggle', label, hint, default: def,
})

export const SETTINGS: SettingCategory[] = [
  /* ==================================================================== */
  {
    id: 'general',
    label: 'General',
    icon: Settings2,
    blurb: 'How the application behaves overall.',
    groups: [
      {
        title: 'Startup',
        settings: [
          {
            id: 'general.projectLocation', kind: 'folder',
            label: 'Default project location',
            hint: 'Where new novels are created.',
            default: 'Documents\\Writing Bot\\Projects',
            note: 'A folder inside OneDrive or Dropbox syncs automatically. ' +
                  'NovelForge retries writes that the sync client has locked.',
          },
          {
            id: 'general.reopenLast', ...onOff(
              'Reopen the last project',
              'Skip the library and go straight back to where you were.',
            ),
          } as Setting,
          {
            id: 'general.startupPage', kind: 'select',
            label: 'Start on', default: 'dashboard',
            options: [
              { value: 'dashboard', label: 'Dashboard' },
              { value: 'editor', label: 'Last scene I was writing' },
              { value: 'library', label: 'Novel library' },
              { value: 'corkboard', label: 'Corkboard' },
            ],
          },
          {
            id: 'general.launchOnStartup', ...onOff(
              'Launch when Windows starts', undefined, false,
            ),
            hint: 'Adds a shortcut to your Startup folder. Removed when off.',
          } as Setting,
        ],
      },
      {
        title: 'Regional',
        settings: [
          {
            id: 'general.language', kind: 'select', label: 'Language',
            default: 'en-GB',
            options: [
              { value: 'en-GB', label: 'English (United Kingdom)' },
              { value: 'en-US', label: 'English (United States)' },
            ],
            note: 'Only English ships today. Translations are welcome as ' +
                  'pull requests - every string lives in one file.',
          },
          {
            id: 'general.dateFormat', kind: 'select', label: 'Date format',
            default: 'dmy',
            options: [
              { value: 'dmy', label: '26 July 2026' },
              { value: 'mdy', label: 'July 26, 2026' },
              { value: 'iso', label: '2026-07-26' },
            ],
          },
          {
            id: 'general.timeFormat', kind: 'select', label: 'Time format',
            default: '24',
            options: [
              { value: '24', label: '24 hour  ·  18:30' },
              { value: '12', label: '12 hour  ·  6:30 pm' },
            ],
          },
          {
            id: 'general.firstDayOfWeek', kind: 'select',
            label: 'Week starts on', default: 'mon',
            hint: 'Used by the writing streak calendar.',
            options: [
              { value: 'mon', label: 'Monday' },
              { value: 'sun', label: 'Sunday' },
            ],
          },
        ],
      },
      {
        title: 'Safety',
        settings: [
          {
            id: 'general.confirmDelete', ...onOff(
              'Confirm before deleting',
              'Always ask before removing a project, chapter or scene.',
            ),
          } as Setting,
          {
            id: 'general.keepFilesOnDelete', ...onOff(
              'Keep documents on disk when deleting',
              'Removes the item from the binder but leaves its Word file ' +
              'in the folder.',
            ),
          } as Setting,
          {
            id: 'general.reset', kind: 'action', default: '',
            label: 'Reset all preferences',
            hint: 'Restores every setting below to its original value. Your ' +
                  'novels, documents and backups are not touched.',
            danger: true, keywords: 'restore defaults factory',
          },
        ],
      },
    ],
  },

  /* ==================================================================== */
  {
    id: 'appearance',
    label: 'Appearance',
    icon: Palette,
    blurb: 'A workspace you can sit in front of for six hours.',
    groups: [
      {
        title: 'Theme',
        settings: [
          {
            id: 'appearance.theme', kind: 'select', label: 'Theme',
            default: 'dark',
            options: [
              { value: 'dark', label: 'Dark', hint: 'Recommended' },
              { value: 'midnight', label: 'Midnight', hint: 'Cooler, indigo' },
              { value: 'amoled', label: 'AMOLED', hint: 'True black' },
              { value: 'sepia', label: 'Sepia', hint: 'Warm paper' },
              { value: 'light', label: 'Light' },
            ],
          },
          {
            id: 'appearance.accent', kind: 'color', label: 'Accent colour',
            default: '#D4AF37',
            hint: 'Used for the active state, progress and highlights.',
          },
          {
            id: 'appearance.followSystem', ...onOff(
              'Follow the system light/dark setting', undefined, false,
            ),
          } as Setting,
        ],
      },
      {
        title: 'Density and scale',
        settings: [
          {
            id: 'appearance.density', kind: 'select', label: 'Interface density',
            default: 'comfortable',
            options: [
              { value: 'compact', label: 'Compact', hint: 'More on screen' },
              { value: 'comfortable', label: 'Comfortable' },
              { value: 'spacious', label: 'Spacious', hint: 'More breathing room' },
            ],
          },
          {
            id: 'appearance.scale', kind: 'slider', label: 'Interface scale',
            default: 100, min: 80, max: 150, step: 5, unit: '%',
          },
          {
            id: 'appearance.radius', kind: 'slider', label: 'Corner roundness',
            default: 12, min: 0, max: 20, step: 2, unit: 'px',
          },
        ],
      },
      {
        title: 'Effects',
        hint: 'Turn these off on an older machine if scrolling feels heavy.',
        settings: [
          {
            id: 'appearance.blur', ...onOff(
              'Window blur on floating panels',
              'The command palette, tooltips and the formatting toolbar.',
            ),
          } as Setting,
          {
            id: 'appearance.sidebarTransparency', kind: 'slider',
            label: 'Sidebar transparency', default: 0, min: 0, max: 40,
            step: 5, unit: '%',
          },
          {
            id: 'appearance.animations', ...onOff(
              'Interface animations',
              'Panel transitions, hover lifts and the sliding sidebar indicator.',
            ),
          } as Setting,
          {
            id: 'appearance.reduceMotion', ...onOff(
              'Respect the system reduced-motion setting', undefined, true,
            ),
          } as Setting,
        ],
      },
      {
        title: 'Layout',
        settings: [
          { id: 'appearance.showLeftSidebar', ...onOff('Show the left sidebar') } as Setting,
          { id: 'appearance.showRightPanel', ...onOff('Show the right panel') } as Setting,
          {
            id: 'appearance.rememberPanels', ...onOff(
              'Remember panel sizes and positions',
            ),
          } as Setting,
          {
            id: 'appearance.editorLayout', kind: 'select',
            label: 'Editor layout', default: 'single',
            options: [
              { value: 'single', label: 'Single page' },
              { value: 'split-notes', label: 'Split - scene and notes' },
              { value: 'split-scene', label: 'Split - two scenes' },
              { value: 'corkboard', label: 'Corkboard' },
            ],
          },
        ],
      },
    ],
  },

  /* ==================================================================== */
  {
    id: 'editor',
    label: 'Writing Editor',
    icon: Type,
    blurb: 'The page itself. This is where you will spend every hour.',
    groups: [
      {
        title: 'Typography',
        settings: [
          {
            id: 'editor.font', kind: 'select', label: 'Writing font',
            default: 'literata',
            options: [
              { value: 'literata', label: 'Literata', hint: 'Made for reading on screen' },
              { value: 'source-serif', label: 'Source Serif' },
              { value: 'crimson', label: 'Crimson Pro' },
              { value: 'ibm-plex-serif', label: 'IBM Plex Serif' },
              { value: 'georgia', label: 'Georgia' },
              { value: 'inter', label: 'Inter', hint: 'Sans serif' },
              { value: 'jetbrains', label: 'JetBrains Mono', hint: 'Monospace' },
            ],
          },
          {
            id: 'editor.fontSize', kind: 'slider', label: 'Font size',
            default: 19, min: 13, max: 32, step: 1, unit: 'px',
          },
          {
            id: 'editor.fontWeight', kind: 'select', label: 'Font weight',
            default: '400',
            options: [
              { value: '300', label: 'Light' },
              { value: '400', label: 'Regular' },
              { value: '500', label: 'Medium' },
            ],
          },
          {
            id: 'editor.lineHeight', kind: 'slider', label: 'Line height',
            default: 178, min: 130, max: 240, step: 2, unit: '%',
          },
          {
            id: 'editor.paragraphSpacing', kind: 'slider',
            label: 'Paragraph spacing', default: 0, min: 0, max: 24,
            step: 2, unit: 'px',
            note: 'Novels traditionally use an indent and no gap. Set a gap ' +
                  'only if you also turn off the first-line indent.',
          },
          {
            id: 'editor.pageWidth', kind: 'slider', label: 'Page width',
            default: 42, min: 30, max: 70, step: 1, unit: 'rem',
            hint: 'Around 60-75 characters a line is easiest to read.',
          },
          {
            id: 'editor.textAlign', kind: 'select', label: 'Alignment',
            default: 'left',
            options: [
              { value: 'left', label: 'Left', hint: 'Recommended on screen' },
              { value: 'justify', label: 'Justified' },
            ],
          },
          {
            id: 'editor.firstLineIndent', ...onOff(
              'Indent the first line of each paragraph',
              'Standard for prose fiction. The first paragraph after a break ' +
              'is never indented.',
            ),
          } as Setting,
        ],
      },
      {
        title: 'Writing experience',
        settings: [
          {
            id: 'editor.typewriter', ...onOff(
              'Typewriter scrolling',
              'Keeps the line you are typing near the middle of the window.',
              false,
            ),
          } as Setting,
          {
            id: 'editor.typewriterPosition', kind: 'slider',
            label: 'Typewriter position', default: 50, min: 25, max: 75,
            step: 5, unit: '% down',
          },
          {
            id: 'editor.focusMode', ...onOff(
              'Focus mode', 'Dims everything except what you are working on.',
              false,
            ),
          } as Setting,
          {
            id: 'editor.focusScope', kind: 'select', label: 'Focus scope',
            default: 'paragraph',
            options: [
              { value: 'sentence', label: 'Sentence' },
              { value: 'paragraph', label: 'Paragraph' },
              { value: 'line', label: 'Line' },
            ],
          },
          {
            id: 'editor.focusOpacity', kind: 'slider',
            label: 'Dimmed text opacity', default: 28, min: 5, max: 60,
            step: 1, unit: '%',
          },
          {
            id: 'editor.highlightLine', ...onOff(
              'Highlight the current line', undefined, false,
            ),
          } as Setting,
          {
            id: 'editor.smoothScroll', ...onOff('Smooth scrolling'),
          } as Setting,
          {
            id: 'editor.smartQuotes', ...onOff(
              'Smart quotes',
              'Turns straight quotes into curly ones as you type.',
            ),
          } as Setting,
          {
            id: 'editor.smartPunctuation', ...onOff(
              'Smart punctuation',
              'Converts -- to an em dash and ... to an ellipsis.',
            ),
          } as Setting,
          {
            id: 'editor.autoIndent', ...onOff('Auto-indent new paragraphs'),
          } as Setting,
          {
            id: 'editor.markdown', ...onOff(
              'Markdown shortcuts',
              '**bold**, *italic* and # headings convert as you type.',
            ),
          } as Setting,
          {
            id: 'editor.spellcheck', ...onOff(
              'Spell check',
              'Uses the dictionary already built into Windows.',
            ),
          } as Setting,
        ],
      },
      {
        title: 'Cursor',
        settings: [
          {
            id: 'editor.cursorWidth', kind: 'slider', label: 'Cursor width',
            default: 2, min: 1, max: 5, step: 1, unit: 'px',
          },
          {
            id: 'editor.cursorBlink', ...onOff('Cursor blinking'),
          } as Setting,
          {
            id: 'editor.cursorAnimation', ...onOff(
              'Animate cursor movement',
              'The caret glides between positions instead of jumping.',
              false,
            ),
          } as Setting,
        ],
      },
    ],
  },

  /* ==================================================================== */
  {
    id: 'backup',
    label: 'Autosave & Backup',
    icon: Save,
    blurb: 'Four independent layers, so losing work takes real effort.',
    groups: [
      {
        title: 'Autosave',
        settings: [
          { id: 'backup.autosave', ...onOff('Autosave') } as Setting,
          {
            id: 'backup.autosaveInterval', kind: 'slider',
            label: 'Autosave after', default: 30, min: 5, max: 300,
            step: 5, unit: 's idle',
            hint: 'Saving also happens whenever you switch away from a scene.',
          },
          {
            id: 'backup.atomicWrites', ...onOff(
              'Crash-safe writes',
              'Every file is written to a temporary name and swapped into ' +
              'place, so an interrupted save can never truncate a document.',
            ),
            note: 'Leave this on. It is the reason a power cut cannot corrupt ' +
                  'a chapter.',
          } as Setting,
        ],
      },
      {
        title: 'Version history',
        settings: [
          {
            id: 'backup.snapshots', ...onOff(
              'Snapshot before every save',
              'Keeps the previous version of each scene so you can go back.',
            ),
          } as Setting,
          {
            id: 'backup.snapshotsPerDoc', kind: 'slider',
            label: 'Versions kept per document', default: 40, min: 5,
            max: 200, step: 5,
          },
        ],
      },
      {
        title: 'Backups',
        settings: [
          {
            id: 'backup.onOpen', ...onOff('Back up when opening a project'),
          } as Setting,
          {
            id: 'backup.onClose', ...onOff('Back up when closing'),
          } as Setting,
          {
            id: 'backup.retention', kind: 'slider', label: 'Backups kept',
            default: 25, min: 3, max: 200, step: 1,
            hint: 'Oldest are pruned automatically.',
          },
          {
            id: 'backup.verify', ...onOff(
              'Verify every backup',
              'Reopens the archive and checks its checksums before reporting ' +
              'success. A backup that fails is deleted rather than left ' +
              'looking valid.',
            ),
          } as Setting,
          {
            id: 'backup.compress', kind: 'select', label: 'Compression',
            default: '6',
            options: [
              { value: '0', label: 'None', hint: 'Fastest' },
              { value: '6', label: 'Balanced' },
              { value: '9', label: 'Maximum', hint: 'Smallest' },
            ],
          },
          {
            id: 'backup.location', kind: 'folder', label: 'Backup folder',
            default: '<project>\\_Backups',
          },
          {
            id: 'backup.export', kind: 'action',
            label: 'Export a backup now',
            hint: 'Writes a verified .zip anywhere you choose.',
            default: '',
          },
        ],
      },
      {
        title: 'Off-machine copies',
        hint: 'NovelForge has no servers, so there is nothing to sync to. ' +
              'Use a folder that already syncs.',
        settings: [
          {
            id: 'backup.cloud', kind: 'toggle', label: 'Cloud backup',
            default: false,
            unavailable:
              'There is no NovelForge cloud, and adding one would mean your ' +
              'manuscript leaving this machine. Put your project folder ' +
              'inside OneDrive, Dropbox or Google Drive instead - it is ' +
              'already handled, including retrying writes the sync client ' +
              'has locked.',
          },
          {
            id: 'backup.gitVersioning', ...onOff(
              'Track changes with Git',
              'If Git is installed, commit the project after each backup. ' +
              'Entirely local unless you add a remote yourself.',
              false,
            ),
          } as Setting,
        ],
      },
    ],
  },

  /* ==================================================================== */
  {
    id: 'analysis',
    label: 'Manuscript Analysis',
    icon: Microscope,
    blurb:
      'Twenty-odd checks that run entirely on your machine. No account, ' +
      'no sign-up, no upload - your manuscript never leaves this computer.',
    groups: [
      {
        title: 'When to run',
        settings: [
          {
            id: 'analysis.enabled', ...onOff('Enable manuscript analysis'),
          } as Setting,
          {
            id: 'analysis.when', kind: 'select', label: 'Run analysis',
            default: 'manual',
            options: [
              { value: 'manual', label: 'Only when I ask', hint: 'F7' },
              { value: 'onSave', label: 'When a scene is saved' },
              { value: 'live', label: 'As I type', hint: 'Uses more CPU' },
            ],
          },
          {
            id: 'analysis.inlineMarks', ...onOff(
              'Underline findings in the text',
              'Off by default. Marks appearing while drafting is exactly the ' +
              'interruption drafting does not need.',
              false,
            ),
          } as Setting,
        ],
      },
      {
        title: 'Prose checks',
        hint: 'Every one of these is a heuristic and some will be wrong. ' +
              'They are worded as observations, never corrections, and ' +
              'nothing is ever rewritten for you.',
        settings: [
          { id: 'analysis.adverbs', ...onOff('Adverbs', '-ly words, with a rate against total word count.') } as Setting,
          { id: 'analysis.filler', ...onOff('Filler and hedging', 'very, really, quite, just, somewhat.') } as Setting,
          { id: 'analysis.filterWords', ...onOff('Filter words', 'she saw, he felt, they noticed - words that put distance between reader and scene.') } as Setting,
          { id: 'analysis.passive', ...onOff('Passive voice') } as Setting,
          { id: 'analysis.saidBookisms', ...onOff('Decorated dialogue tags', 'expostulated, chortled, ejaculated.') } as Setting,
          { id: 'analysis.impossibleTags', ...onOff('Impossible speech tags', 'You cannot smile a sentence.') } as Setting,
          { id: 'analysis.dialoguePunctuation', ...onOff('Dialogue punctuation', 'Commas inside quotes, lowercase tags, balanced marks.') } as Setting,
          { id: 'analysis.rhythm', ...onOff('Sentence rhythm', 'Uniform sentence lengths, over-long sentences, runs of the same length.') } as Setting,
          { id: 'analysis.echoes', ...onOff('Word echoes', 'Distinctive words repeated close together.') } as Setting,
          { id: 'analysis.openings', ...onOff('Repeated openings', 'Paragraphs and sentences starting the same way.') } as Setting,
          { id: 'analysis.cliches', ...onOff('Stock phrases') } as Setting,
          { id: 'analysis.senses', ...onOff('Sensory coverage', 'Which of the five senses appear. Smell and taste are the most under-used.') } as Setting,
          { id: 'analysis.dialogueRatio', ...onOff('Dialogue balance') } as Setting,
          { id: 'analysis.readability', ...onOff('Readability', 'Flesch reading ease and grade level.') } as Setting,
          { id: 'analysis.mechanics', ...onOff('Mechanics', 'Double spaces, doubled words, leftover [bracket tags].') } as Setting,
        ],
      },
      {
        title: 'Structure checks',
        settings: [
          {
            id: 'analysis.craftCheck', ...onOff(
              'Scene craft check',
              'Does the scene have a goal, opposition, a turn and a value ' +
              'shift? Reads the scene card, not the prose.',
            ),
          } as Setting,
          {
            id: 'analysis.threadGaps', ...onOff(
              'Warn about neglected plot threads',
              'A thread absent for many consecutive scenes reads as abandoned.',
            ),
          } as Setting,
          {
            id: 'analysis.threadGapSize', kind: 'slider',
            label: 'Warn after', default: 8, min: 3, max: 30, step: 1,
            unit: ' scenes',
          },
          {
            id: 'analysis.povBalance', ...onOff('Track point-of-view balance'),
          } as Setting,
        ],
      },
      {
        title: 'Thresholds',
        settings: [
          {
            id: 'analysis.adverbRate', kind: 'slider',
            label: 'Flag adverbs above', default: 2.0, min: 0.5, max: 6,
            step: 0.1, unit: '% of words',
          },
          {
            id: 'analysis.longSentence', kind: 'slider',
            label: 'Flag sentences longer than', default: 45, min: 25,
            max: 90, step: 5, unit: ' words',
          },
          {
            id: 'analysis.readabilityTarget', kind: 'select',
            label: 'Target readability', default: 'commercial',
            options: [
              { value: 'middle-grade', label: 'Middle grade', hint: 'Ease 70+' },
              { value: 'commercial', label: 'Commercial fiction', hint: 'Ease 60-70' },
              { value: 'upmarket', label: 'Upmarket / literary', hint: 'Ease 50-60' },
              { value: 'none', label: 'No target' },
            ],
          },
        ],
      },
    ],
  },

  /* ==================================================================== */
  {
    id: 'projects',
    label: 'Projects',
    icon: FolderTree,
    blurb: 'Defaults applied when you create something new.',
    groups: [
      {
        title: 'New novels',
        settings: [
          {
            id: 'projects.structure', kind: 'select',
            label: 'Default story structure', default: 'three_act',
            options: [
              { value: 'three_act', label: 'Three-Act', hint: 'Weiland percentages' },
              { value: 'save_the_cat', label: 'Save the Cat!', hint: '15 beats' },
              { value: 'seven_point', label: 'Seven-Point', hint: 'Dan Wells' },
              { value: 'story_circle', label: 'Story Circle', hint: 'Harmon' },
              { value: 'heros_journey', label: "Hero's Journey", hint: 'Vogler' },
              { value: 'romance_beat', label: 'Romancing the Beat' },
              { value: 'mystery', label: 'Mystery / Crime' },
              { value: 'freytag', label: "Freytag's Pyramid" },
              { value: 'snowflake', label: 'Snowflake Method' },
            ],
          },
          {
            id: 'projects.targetWords', kind: 'number',
            label: 'Default target length', default: 90000, unit: 'words',
          },
          {
            id: 'projects.packs', kind: 'select',
            label: 'Template packs', default: 'all',
            options: [
              { value: 'all', label: 'All of them' },
              { value: 'fantasy', label: 'Fantasy / Sci-Fi', hint: 'Full world bible' },
              { value: 'mystery', label: 'Mystery', hint: 'Clue tracker' },
              { value: 'romance', label: 'Romance', hint: 'Relationship arc' },
              { value: 'literary', label: 'Literary', hint: 'Lighter worldbuilding' },
            ],
          },
        ],
      },
      {
        title: 'Numbering',
        settings: [
          {
            id: 'projects.autoNumberChapters', ...onOff('Number chapters automatically'),
          } as Setting,
          {
            id: 'projects.chapterNumberStyle', kind: 'select',
            label: 'Chapter numbering', default: 'word',
            options: [
              { value: 'word', label: 'Chapter One' },
              { value: 'digit', label: 'Chapter 1' },
              { value: 'roman', label: 'Chapter I' },
              { value: 'none', label: 'No number' },
            ],
          },
          {
            id: 'projects.numberScenes', ...onOff('Number scenes within chapters', undefined, false),
          } as Setting,
          {
            id: 'projects.sceneSeparator', kind: 'select',
            label: 'Scene break marker', default: '#',
            options: [
              { value: '#', label: '#' },
              { value: '* * *', label: '* * *' },
              { value: '---', label: '---' },
              { value: '~', label: '~' },
            ],
          },
        ],
      },
      {
        title: 'Housekeeping',
        settings: [
          {
            id: 'projects.archiveCompleted', ...onOff(
              'Move finished novels to an Archive folder', undefined, false,
            ),
          } as Setting,
          {
            id: 'projects.coverImages', ...onOff(
              'Show cover art in the library',
              'Drop a cover.jpg into a project folder and it appears on its card.',
            ),
          } as Setting,
          {
            id: 'projects.trackMetadata', ...onOff(
              'Keep genre, status and comparable titles',
            ),
          } as Setting,
        ],
      },
    ],
  },

  /* ==================================================================== */
  {
    id: 'goals',
    label: 'Word Goals',
    icon: Target,
    blurb: 'Targets, streaks and timers.',
    groups: [
      {
        title: 'Targets',
        settings: [
          { id: 'goals.daily', kind: 'number', label: 'Daily goal', default: 1000, unit: 'words' },
          { id: 'goals.weekly', kind: 'number', label: 'Weekly goal', default: 6000, unit: 'words' },
          { id: 'goals.monthly', kind: 'number', label: 'Monthly goal', default: 25000, unit: 'words' },
          { id: 'goals.session', kind: 'number', label: 'Session goal', default: 500, unit: 'words' },
          {
            id: 'goals.countDeletions', kind: 'select',
            label: 'Count a revision day as', default: 'added',
            options: [
              { value: 'added', label: 'Words typed', hint: 'Recommended' },
              { value: 'net', label: 'Net change', hint: 'Can go negative' },
            ],
            note: 'Cutting 800 words and writing 600 is real work. Counting ' +
                  'it as -200 is both discouraging and wrong, so targets ' +
                  'measure what you typed.',
          },
        ],
      },
      {
        title: 'Streaks and timers',
        settings: [
          { id: 'goals.streaks', ...onOff('Track a writing streak') } as Setting,
          {
            id: 'goals.streakMinimum', kind: 'number',
            label: 'Words needed to keep a streak', default: 1, unit: 'words',
            hint: 'One word counts. Showing up is the habit.',
          },
          { id: 'goals.sessionTimer', ...onOff('Session timer') } as Setting,
          {
            id: 'goals.sprintLength', kind: 'slider', label: 'Sprint length',
            default: 25, min: 5, max: 90, step: 5, unit: ' min',
          },
          {
            id: 'goals.pomodoro', ...onOff(
              'Break reminders', 'Suggest a break after each sprint.', false,
            ),
          } as Setting,
          {
            id: 'goals.breakLength', kind: 'slider', label: 'Break length',
            default: 5, min: 2, max: 30, step: 1, unit: ' min',
          },
        ],
      },
      {
        title: 'Deadline',
        settings: [
          { id: 'goals.deadline', kind: 'text', label: 'Deadline', default: '', hint: 'YYYY-MM-DD. Leave blank for no countdown.' },
          {
            id: 'goals.adaptiveTarget', ...onOff(
              'Recalculate the daily target from the deadline',
              'Words remaining divided by days remaining, updated each morning.',
              false,
            ),
          } as Setting,
        ],
      },
    ],
  },

  /* ==================================================================== */
  {
    id: 'notifications',
    label: 'Notifications',
    icon: Bell,
    blurb: 'All local. Nothing is ever sent anywhere.',
    groups: [
      {
        title: 'Show me',
        settings: [
          { id: 'notify.goalReached', ...onOff('Daily goal reached') } as Setting,
          { id: 'notify.streakRisk', ...onOff('Streak about to break', 'A quiet nudge in the evening.') } as Setting,
          { id: 'notify.backupDone', ...onOff('Backup finished', undefined, false) } as Setting,
          { id: 'notify.analysisDone', ...onOff('Analysis finished') } as Setting,
          { id: 'notify.sprintEnd', ...onOff('Sprint finished') } as Setting,
          { id: 'notify.milestones', ...onOff('Milestones', 'First 10,000 words, halfway, first draft finished.') } as Setting,
          { id: 'notify.updates', ...onOff('An update is available', undefined, false) } as Setting,
        ],
      },
      {
        title: 'How',
        settings: [
          {
            id: 'notify.style', kind: 'select', label: 'Style', default: 'toast',
            options: [
              { value: 'toast', label: 'In-app toast' },
              { value: 'system', label: 'Windows notification' },
              { value: 'statusbar', label: 'Status bar only', hint: 'Quietest' },
            ],
          },
          { id: 'notify.sound', ...onOff('Play a sound', undefined, false) } as Setting,
          {
            id: 'notify.quietWhileWriting', ...onOff(
              'Stay silent while I am typing',
              'Holds notifications until you pause for a minute.',
            ),
          } as Setting,
        ],
      },
    ],
  },

  /* ==================================================================== */
  {
    id: 'shortcuts',
    label: 'Keyboard',
    icon: Keyboard,
    blurb: 'Every command can be rebound.',
    groups: [
      {
        title: 'Essentials',
        settings: [
          { id: 'key.palette', kind: 'shortcut', label: 'Command palette', default: 'Ctrl K' },
          { id: 'key.save', kind: 'shortcut', label: 'Save', default: 'Ctrl S' },
          { id: 'key.search', kind: 'shortcut', label: 'Find in project', default: 'Ctrl F' },
          { id: 'key.newScene', kind: 'shortcut', label: 'New scene', default: 'Ctrl N' },
          { id: 'key.newChapter', kind: 'shortcut', label: 'New chapter', default: 'Ctrl Shift C' },
        ],
      },
      {
        title: 'View',
        settings: [
          { id: 'key.focus', kind: 'shortcut', label: 'Focus mode', default: 'F11' },
          { id: 'key.zen', kind: 'shortcut', label: 'Zen mode', default: 'F12' },
          { id: 'key.toggleSidebar', kind: 'shortcut', label: 'Toggle sidebar', default: 'Ctrl \\' },
          { id: 'key.corkboard', kind: 'shortcut', label: 'Corkboard', default: 'Ctrl K' },
        ],
      },
      {
        title: 'Manuscript',
        settings: [
          { id: 'key.compile', kind: 'shortcut', label: 'Compile', default: 'F5' },
          { id: 'key.analyse', kind: 'shortcut', label: 'Analyse scene', default: 'F7' },
          { id: 'key.craftCheck', kind: 'shortcut', label: 'Craft check', default: 'F8' },
          { id: 'key.stats', kind: 'shortcut', label: 'Statistics', default: 'F9' },
          { id: 'key.sprint', kind: 'shortcut', label: 'Start a sprint', default: 'F6' },
        ],
      },
      {
        title: 'Profiles',
        settings: [
          { id: 'key.reset', kind: 'action', label: 'Reset all shortcuts', default: '', danger: true },
          { id: 'key.export', kind: 'action', label: 'Export shortcut profile', default: '' },
          { id: 'key.import', kind: 'action', label: 'Import shortcut profile', default: '' },
        ],
      },
    ],
  },

  /* ==================================================================== */
  {
    id: 'export',
    label: 'Export',
    icon: Download,
    blurb: 'Your book, in whatever shape the next person needs it.',
    groups: [
      {
        title: 'Format',
        settings: [
          {
            id: 'export.format', kind: 'select', label: 'Default format',
            default: 'docx',
            options: [
              { value: 'docx', label: 'Word (.docx)', hint: 'Ready now' },
              { value: 'txt', label: 'Plain text', hint: 'Ready now' },
              { value: 'md', label: 'Markdown', hint: 'Ready now' },
              { value: 'html', label: 'HTML', hint: 'Ready now' },
              { value: 'epub', label: 'EPUB 3', hint: 'In progress' },
              { value: 'pdf', label: 'PDF', hint: 'In progress' },
              { value: 'rtf', label: 'RTF', hint: 'In progress' },
            ],
            note: 'Word and plain text are fully implemented and tested. ' +
                  'EPUB, PDF and RTF are being built - they are listed so ' +
                  'you can see what is coming, not to pretend they work.',
          },
          {
            id: 'export.preset', kind: 'select', label: 'Preset',
            default: 'submission',
            options: [
              { value: 'submission', label: 'Agent submission', hint: 'Standard manuscript format' },
              { value: 'working', label: 'Working draft', hint: 'With synopses and status' },
              { value: 'ebook', label: 'E-book' },
              { value: 'print', label: 'Print interior' },
              { value: 'beta', label: 'For beta readers' },
            ],
          },
        ],
      },
      {
        title: 'Page',
        settings: [
          {
            id: 'export.pageSize', kind: 'select', label: 'Page size',
            default: 'letter',
            options: [
              { value: 'letter', label: 'US Letter', hint: '8.5 x 11 in' },
              { value: 'a4', label: 'A4', hint: '210 x 297 mm' },
              { value: '6x9', label: 'Trade paperback', hint: '6 x 9 in' },
              { value: '5x8', label: 'Digest', hint: '5 x 8 in' },
            ],
          },
          { id: 'export.margin', kind: 'slider', label: 'Margin', default: 1, min: 0.5, max: 2, step: 0.05, unit: ' in' },
          { id: 'export.mirrorMargins', ...onOff('Mirrored margins for print', 'Adds a gutter on the binding edge.', false) } as Setting,
          {
            id: 'export.font', kind: 'select', label: 'Manuscript font',
            default: 'Times New Roman',
            options: [
              { value: 'Times New Roman', label: 'Times New Roman', hint: 'Industry default' },
              { value: 'Courier New', label: 'Courier New', hint: 'Classic Shunn' },
              { value: 'Georgia', label: 'Georgia' },
              { value: 'Garamond', label: 'Garamond' },
            ],
          },
          { id: 'export.fontSize', kind: 'number', label: 'Font size', default: 12, unit: 'pt' },
          {
            id: 'export.lineSpacing', kind: 'select', label: 'Line spacing',
            default: '2',
            options: [
              { value: '2', label: 'Double', hint: 'Required for submission' },
              { value: '1.5', label: 'One and a half' },
              { value: '1', label: 'Single' },
            ],
          },
        ],
      },
      {
        title: 'Include',
        settings: [
          { id: 'export.titlePage', ...onOff('Title page', 'Contact block and rounded word count.') } as Setting,
          { id: 'export.runningHeader', ...onOff('Running header', 'Surname / TITLE / page, from page two.') } as Setting,
          { id: 'export.chapterTitles', ...onOff('Chapter titles') } as Setting,
          { id: 'export.toc', ...onOff('Table of contents', undefined, false) } as Setting,
          { id: 'export.coverPage', ...onOff('Cover image', undefined, false) } as Setting,
          { id: 'export.frontMatter', ...onOff('Front matter', 'Copyright, dedication, epigraph.', false) } as Setting,
          { id: 'export.theEnd', ...onOff('“THE END” at the end') } as Setting,
          { id: 'export.metadata', ...onOff('Embed metadata', 'Title, author, genre, ISBN.') } as Setting,
        ],
      },
    ],
  },

  /* ==================================================================== */
  {
    id: 'privacy',
    label: 'Privacy & Security',
    icon: Shield,
    blurb: 'Your writing belongs to you. This is not a slogan here.',
    groups: [
      {
        title: 'What leaves this machine',
        hint: 'Nothing, unless you turn on update checks below.',
        settings: [
          {
            id: 'privacy.telemetry', kind: 'toggle', label: 'Usage analytics',
            default: false,
            unavailable:
              'There is none to disable. NovelForge collects no analytics, ' +
              'has no servers and makes no network requests except the ' +
              'update check, which is off by default.',
          },
          {
            id: 'privacy.deleteAccount', kind: 'toggle', label: 'Delete account',
            default: false,
            unavailable:
              'There are no accounts. Nothing to sign up for, nothing to ' +
              'delete, nothing to lose access to. Your novels are files in ' +
              'a folder you already own.',
          },
        ],
      },
      {
        title: 'On this machine',
        settings: [
          {
            id: 'privacy.passwordLock', ...onOff(
              'Lock with a password', 'Asked for when the app starts.', false,
            ),
          } as Setting,
          {
            id: 'privacy.encrypt', ...onOff(
              'Encrypt project files at rest', undefined, false,
            ),
            note: 'Encrypted projects can no longer be opened directly in ' +
                  'Word. That is a real trade-off - most writers should ' +
                  'leave this off and use Windows BitLocker instead.',
          } as Setting,
          {
            id: 'privacy.sessionTimeout', kind: 'slider',
            label: 'Lock after inactivity', default: 0, min: 0, max: 120,
            step: 5, unit: ' min', hint: 'Zero never locks.',
          },
          { id: 'privacy.clearCache', kind: 'action', label: 'Clear cached data', default: '' },
          { id: 'privacy.clearRecent', kind: 'action', label: 'Clear recent files list', default: '' },
          {
            id: 'privacy.exportAll', kind: 'action',
            label: 'Export everything',
            hint: 'Every project, document and backup as one archive. No ' +
                  'lock-in - you can walk away at any time.',
            default: '',
          },
        ],
      },
    ],
  },

  /* ==================================================================== */
  {
    id: 'performance',
    label: 'Performance',
    icon: Gauge,
    blurb: 'Matters once a novel passes a few hundred scenes.',
    groups: [
      {
        title: 'Rendering',
        settings: [
          {
            id: 'perf.gpu', ...onOff(
              'Hardware acceleration',
              'Turn off if the window flickers or tears.',
            ),
          } as Setting,
          {
            id: 'perf.animations', ...onOff('Animate panel transitions'),
          } as Setting,
          {
            id: 'perf.virtualise', ...onOff(
              'Virtualise long lists',
              'Only renders rows on screen. Keeps a 3,000-scene binder fast.',
            ),
          } as Setting,
        ],
      },
      {
        title: 'Documents',
        hint: 'Word counts come from the manifest, so opening a project ' +
              'never parses a document. These control the rarer heavy passes.',
        settings: [
          {
            id: 'perf.reloadStrategy', kind: 'select',
            label: 'Pick up edits made in Word', default: 'timestamps',
            options: [
              { value: 'timestamps', label: 'Changed files only', hint: 'Recommended' },
              { value: 'always', label: 'Re-read everything', hint: 'Slow' },
              { value: 'manual', label: 'Only when I ask' },
            ],
            note: 'Comparing timestamps reads one file instead of hundreds. ' +
                  'On a 240-scene novel that is 11 milliseconds against 11 ' +
                  'seconds.',
          },
          {
            id: 'perf.indexOnIdle', ...onOff(
              'Build the search index while idle',
              'Makes full-text search instant at the cost of some background ' +
              'work.',
            ),
          } as Setting,
          {
            id: 'perf.cacheLimit', kind: 'slider', label: 'Document cache',
            default: 200, min: 20, max: 2000, step: 20, unit: ' documents',
          },
          { id: 'perf.clearCaches', kind: 'action', label: 'Clear caches and re-index', default: '' },
        ],
      },
      {
        title: 'Maps',
        settings: [
          {
            id: 'perf.mapQuality', kind: 'select', label: 'Map export quality',
            default: '2',
            options: [
              { value: '1', label: 'Standard', hint: 'Fastest' },
              { value: '2', label: 'High', hint: 'Recommended' },
              { value: '3', label: 'Maximum', hint: 'Slowest, best for print' },
            ],
            hint: 'Supersampling factor. Higher renders smoother lines.',
          },
          {
            id: 'perf.mapLivePreview', ...onOff(
              'Show the parchment texture while editing',
              'Turn off on a slow machine; exports are unaffected.',
            ),
          } as Setting,
        ],
      },
    ],
  },

  /* ==================================================================== */
  {
    id: 'updates',
    label: 'Updates',
    icon: RefreshCw,
    blurb: 'Entirely optional and off by default.',
    groups: [
      {
        title: 'Checking',
        settings: [
          {
            id: 'updates.check', ...onOff(
              'Check for updates',
              'Asks GitHub whether a newer release exists. This is the only ' +
              'network request the application ever makes.',
              false,
            ),
          } as Setting,
          {
            id: 'updates.frequency', kind: 'select', label: 'Check',
            default: 'weekly',
            options: [
              { value: 'startup', label: 'Every time it starts' },
              { value: 'daily', label: 'Once a day' },
              { value: 'weekly', label: 'Once a week' },
            ],
          },
          {
            id: 'updates.channel', kind: 'select', label: 'Release channel',
            default: 'stable',
            options: [
              { value: 'stable', label: 'Stable', hint: 'Recommended' },
              { value: 'beta', label: 'Beta', hint: 'Early, may break' },
            ],
          },
          { id: 'updates.checkNow', kind: 'action', label: 'Check now', default: '' },
          { id: 'updates.releaseNotes', kind: 'action', label: 'Read the release notes', default: '' },
        ],
      },
    ],
  },

  /* ==================================================================== */
  {
    id: 'about',
    label: 'About',
    icon: Info,
    blurb: 'Free, open source, and yours to keep.',
    groups: [
      {
        title: 'This build',
        settings: [
          { id: 'about.version', kind: 'info', label: 'Version', default: '2.0.0' },
          { id: 'about.licence', kind: 'info', label: 'Licence', default: 'MIT' },
          { id: 'about.engine', kind: 'info', label: 'Engine', default: 'Python 3.13' },
        ],
      },
      {
        title: 'Project',
        settings: [
          { id: 'about.github', kind: 'action', label: 'GitHub repository', default: '' },
          { id: 'about.docs', kind: 'action', label: 'Documentation', default: '' },
          { id: 'about.bug', kind: 'action', label: 'Report a bug', default: '' },
          { id: 'about.feature', kind: 'action', label: 'Request a feature', default: '' },
          { id: 'about.changelog', kind: 'action', label: 'Changelog', default: '' },
          {
            id: 'about.donate', kind: 'action', label: 'Support this project',
            hint: 'NovelForge is free and always will be. If it helped you ' +
                  'finish something, a donation keeps it being built.',
            default: '',
          },
        ],
      },
      {
        title: 'Credits',
        settings: [
          {
            id: 'about.libraries', kind: 'action',
            label: 'Open source libraries', default: '',
            hint: 'python-docx, Pillow, React, Next.js, Radix, Framer Motion, ' +
                  'Lucide, Tailwind.',
          },
          {
            id: 'about.frameworks', kind: 'info', label: 'Craft frameworks',
            default: 'Weiland · Snyder · Wells · Harmon · Vogler · Hayes · ' +
                     'Ingermanson · Swain · Shunn',
          },
        ],
      },
    ],
  },
]

/** Every setting, flattened - used by search and by reset-to-defaults. */
export const ALL_SETTINGS: (Setting & {
  category: string
  categoryLabel: string
  group: string
})[] = SETTINGS.flatMap((category) =>
  category.groups.flatMap((group) =>
    group.settings.map((setting) => ({
      ...setting,
      category: category.id,
      categoryLabel: category.label,
      group: group.title,
    })),
  ),
)

export const DEFAULTS: Record<string, string | number | boolean> =
  Object.fromEntries(ALL_SETTINGS.map((s) => [s.id, s.default]))

export function searchSettings(query: string) {
  const q = query.trim().toLowerCase()
  if (!q) return []
  return ALL_SETTINGS.filter((s) =>
    [s.label, s.hint, s.note, s.categoryLabel, s.group, s.keywords]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(q),
  ).slice(0, 40)
}
