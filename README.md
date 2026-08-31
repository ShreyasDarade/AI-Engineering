# Nine Over Tioga

A phone-first trip hub for nine friends in Yosemite over Labor Day weekend 2026
(Fri 4 – Tue 8 September), built as a single self-contained HTML page.

**Live:** https://claude.ai/code/artifact/c3686728-cd0b-42a6-b772-d6e02b381f8c

## What it does

Nine tabs, all usable with no network once the page has loaded:

| Tab | What it's for |
|---|---|
| **Now** | Live trip clock. What's happening this minute, a countdown to the next hard deadline, sun times, and a ribbon of the whole day. |
| **Plan** | The itinerary as a **time-budget engine** — every stop and drive leg carries a duration, the day sums itself, and it reports when you actually get back. Saturday and Sunday each have selectable variants with the arrival math side by side. |
| **Drive** | Sonora Pass vs through-the-park, the full fuel plan (there is no gas in Yosemite Valley), and links out to live road, webcam, AQI and fire sources. |
| **Crowds** | Hour-by-hour rush levels for eight locations, modelled from reported holiday patterns. Clearly labelled as estimates, not a live feed. |
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
- **Runtime capabilities:** `sample` (in-app trip Q&A) and `downloads` (recap +
  offline copy). Both degrade to hidden when `claude.use()` returns `null`.
  Live multi-device sync via `db` is deliberately not declared — it would make
  the artifact organization-internal and block sharing outside the owner's
  Claude workspace.
- **Themes.** Full light and dark token sets defined at bare `:root`, under
  `prefers-color-scheme`, and under `[data-theme]`, so all three viewer states
  resolve.

## Verified

Walked all nine tabs in Chromium at 320 / 390 / 430 px with no horizontal
overflow and no console errors; interaction pass covers identity, variant
switching, voting, rating, packing, car moves, check-ins, log posting and
reload persistence.
