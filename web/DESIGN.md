# DESIGN.md: the home-server page

Components come from strata-react. Follows `ux-research/ux-design/skill/assets/DESIGN.template.md`, trimmed to what this page decides.

- **Mode**: Operate. People open it to check on the machine, not to be persuaded.
- **The one question**: "Is everything on this machine OK, and if not, what?" **The finding** is the
  line under the title, computed by the server (`render.finding`, also in the JSON): failed units, a
  disk at 90% or more, CPU high for a minute (with the top process), memory, apps behind their code,
  else "All good".
- **Signature**: the two history charts (CPU, memory used by programs), each a 2px line with direct
  labels, and the memory bar that shows where the RAM goes. Everything else is standard controls.
- **Colour**: seeds `#2f6f5e` (the page's existing teal, kept for continuity) and `#b7791f` (amber,
  the "caution" role). Generated with `palette.mjs --contrast 0.5`; 42 checks pass. Status roles
  (success, warning, danger, info) are kept apart from the accent and always carry a word.
- **Type**: the system UI font, one family. The page is served from a home server and should not wait
  on a font download; tabular figures everywhere numbers move.
- **Motion**: none beyond the shared 150-250 ms state transitions and the 2% button press. The charts
  redraw as data arrives and nothing animates in.
- **Character**: at rest only. Plain, exact words ("Code newer: a → b", "Cached files, reclaimable").
  No illustrations, no emoji.
- **Not chosen**: sparklines on every metric, gradient or filled areas, a coloured sidebar, a
  stacked-area memory history (the composition is the bar and table; the trend is the line).
