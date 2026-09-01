# Yosemite Standard Time

A phone-first trip hub for nine friends in Yosemite over Labor Day weekend 2026
(Fri 4 – Tue 8 September), built as a single self-contained HTML page.

**Live:** https://claude.ai/code/artifact/c3686728-cd0b-42a6-b772-d6e02b381f8c

## What it does

Eight tabs, all usable with no network once the page has loaded:

| Tab | What it's for |
|---|---|
| **Now** | Live trip clock. What's happening this minute, a countdown to the next hard deadline, sun times, and a ribbon of the whole day. |
| **Plan** | Lodging base toggle, plus the itinerary as a **time-budget engine** — every stop and drive leg carries a duration, the day sums itself, and it reports when you actually get back. Saturday and Sunday each have selectable variants with the arrival math side by side. |
| **Roads** | Sonora Pass vs through-the-park, the full fuel plan (there is no gas in Yosemite Valley), links out to live road/webcam/AQI/fire sources, and hour-by-hour rush levels for eight locations (modelled from reported holiday patterns, not a live feed). |
| **Map** | Hand-drawn SVG schematics of the loop and eastern Yosemite Valley — no tiles, no network. Numbered pins tap out to real navigation. |
| **Do** | Activities with distance, gain, time and difficulty. Vote before, star-rate after. |
| **Crew** | Three cars, packing list, check-ins, and Monday's airport/home split. |
| **No signal** | A one-screen card built to be screenshotted before service dies. |
| **Log** | Shared journal, ratings roundup, and a downloadable trip recap. |

## Design notes

- **Offline first.** All content is baked into the page. State mirrors to
  `localStorage`, wrapped so a blocked storage API can't take the page down.
  The Valley, Tioga Road and Glacier Point have effectively no cell service.
- **The time-budget engine** (`runChain` / `verdictFor`) is the core. Change one
  `min` value in `DAYS` and every downstream arrival time re-computes.
- **Only the visible tab is built.** `render()` renders the active panel and
  nothing else, so a checkbox tick touches one panel instead of eight — 0.8 ms
  and 245 live DOM nodes, against 10.5 ms and 1,640 when every tab was rebuilt.
- **Runtime capabilities:** `db` (shared live state) and `downloads` (recap +
  offline copy). Both degrade gracefully
  when `claude.use()` returns `null` — with no `db` the app still works fully,
  backed by `localStorage`, and says so in the sync banner. Note that declaring
  `db` makes the artifact organization-internal: viewers must be signed into
  the owner's Claude workspace.
- **Lodging base toggle.** `BASES` holds two bases (Coarsegold and inside
  Yosemite Valley) with their own start times and drive legs. Steps built with
  `DL()` resolve their duration from the active base, so switching re-times all
  four days. The No Signal card derives its times from the same engine via
  `offlineRows()`, so it cannot drift from the plan.
- **Themes.** Full light and dark token sets defined at bare `:root`, under
  `prefers-color-scheme`, and under `[data-theme]`, so all three viewer states
  resolve.

## Verified

Walked all eight tabs in Chromium at 320 / 390 / 430 px with no horizontal
overflow and no console errors; interaction pass covers identity, variant
switching, voting, rating, packing, car moves, check-ins, log posting and
reload persistence; both lodging bases re-time all four days correctly and the
No Signal card stays in step with the engine.
