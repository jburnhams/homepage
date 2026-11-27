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
- **Over time** (added 2026-11-25): the question is "where did the machine's time go?". Tabs for last hour, 24 hours and week; the server's one-sentence verdict first, then four charts (CPU, memory, busiest disk, GPU), then a table where every resource has a word for how often it was over its limit ("Fine", "Sometimes 8 %", "Often 12 %"), then who was running when programs waited, then services by use. Charts use the same 2px line as above; no stacked areas. On a phone the tables keep the name, the verdict word and the main figure.
- **Spinning disks** (added 2026-11-27): under the charts, "what was running when it waited" names the disks that were busy and who moved data on them, with the folder. A table lists what uses the spinning disks, each marked **Steady, move?** (active in at least 3 hours or a quarter of them) or **Bursts**: the point is to move steady users to the SSD and leave occasional big-file work on the spinning disks.
