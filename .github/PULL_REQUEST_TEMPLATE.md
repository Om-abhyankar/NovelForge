## What this changes

<!-- One or two sentences: what does this PR do, and why? -->

## How you tested it

<!-- There's no automated test suite yet (see CLAUDE.md). Describe what you
     actually did to check this works - which windows you opened, what you
     clicked, what you'd expect someone reviewing this to try themselves. -->

## Checklist

- [ ] This is one scoped change, not several unrelated ones bundled together
- [ ] Any new or moved window still fits the screen (goes through
      `center_window()` in `novelforge/ui/widgets.py`, not `.geometry()`)
- [ ] Nothing writes prose into `project.json` - `.docx` files stay the
      source of truth
- [ ] I ran the app and actually exercised the changed feature
