# Generative improvements: qualification and listening

Date: 2026-10-31. Fixtures use seed 1729, C major, 120 BPM, eighth-note
pattern steps, three song voices and three/four fugue voices. They contain no
program changes: use the same receiving synth, patch, effects and output gain.
The baseline source revision is `f117892c12c3c44ca293928fd41fd26c841de7ad`.
Each manifest includes hashes of its source files and exported MIDI.

## Evidence and reproduction

- `baseline/`: actual archived pre-change source, original events and MIDI.
- `current/`: current source events, MIDI, harmony/motif metadata and metrics.
- `current/comparison/`: diagnostic pairs with equal per-bar onset counts and
  normalized mean velocity. Seeded thinning changes phrasing: use these only to
  check density/loudness bias, then return to the original performances.
- Baseline song events lack stable voice identity; unavailable metrics are null.
  Dissonance observations include intentional blues sevenths and are not failure
  counts. Fugue tonal costs describe preparation/resolution; neither that cost
  nor fewer crossings proves better music.
- Current exports retain the voice identity of each emitted attack, including
  ornaments consumed from earlier quarter-beat rows at the playback step.
- `timing-*.json`: sleep-only baseline, bounded-spin baseline, and generation load.
  `*-initial.json` preserves the long-sleep attempt before capped-sleep tuning.
  Deadline error includes every observed outlier. CPU is parent-process CPU only;
  spawned renderer CPU is not included. MIDI uses a fake sink, not a device.
- `backend-tests.txt`: completed backend run with localhost access.

Run all Python with `.venv/bin/python` or `.venv/bin/pytest`. Export current material:

```sh
.venv/bin/python tools/evaluate_generative_music.py --output docs/validation/generative-engine/improvements/current --comparison-baseline docs/validation/generative-engine/improvements/baseline
.venv/bin/python tools/check_generative_timing.py --seconds 12
.venv/bin/pytest tests -q -o addopts=''
```

For baseline regeneration, extract that revision's `src/` into a temporary folder
with `git archive`, then pass that folder as `--source-root` and the exact revision
as `--revision`. The exporter deliberately disables song tempo factors for equal-
tempo listening comparisons; production preserves those factors. Event/MIDI export
is offline evidence, not a recording of live MIDI timing.

## Manual acceptance worksheet

Use PASS / FAIL / BLOCKED / N/A per item. Record synth, patch, gain, date, reviewer,
input device, host and notes. Current status of all items below: **BLOCKED — requires
listening or the intended hardware; not performed by automated tests.**

- [ ] Harmony: compare baseline/current raw verse and blues fixtures. Expect audible
  departure/return and twelve-bar I/IV/V movement. Status: ___ Evidence/notes: ___
- [ ] Identity: compare first and returning choruses. Expect recognizable first-half
  pitch/rhythm with second-half development. Status: ___ Evidence/notes: ___
- [ ] Texture: listen for stable bass, independent inner parts and phrase-end space.
  Check matched-density pairs for loudness bias. Status: ___ Evidence/notes: ___
- [ ] Minimalist: confirm tonic drone/modal character remains appropriate.
  Status: ___ Evidence/notes: ___
- [ ] Fugue: listen to prepared/resolved chromatic notes and voice ordering. Do not
  infer acceptance from the optimizer score. Status: ___ Evidence/notes: ___
- [ ] Retrigger: on the target synth, overlap same-pitch voices; expect an explicit
  new attack without an old deadline cutting it short. Stop must release all notes.
  Status: ___ Evidence/notes: ___
- [ ] Timing: run the timing tool on supported Raspberry Pi hardware under normal
  MIDI and input load; independently measure device response. Require <2 ms tick
  jitter and <10 ms button response. Status: ___ Evidence/notes: ___

## Operational behavior

Generation is process-isolated, bounded to one pending job and one ready result per
mode. Delayed preparation stays silent; no synchronous fallback runs on a tick.
Failed work logs and retries after five seconds with the same composition seed.
Song scale/root/voice edits rebuild in the worker and adopt at an elapsed bar;
late results defer adoption. Division changes keep the existing next-step contract.
New compositions advance the private seed stream. Existing configuration/API/CLI
names and persistence behavior are unchanged.

The output worker owns note-on and note-off ordering, expands channel 0 to channels
1–16, and flushes active notes on shutdown. Queue overflow drops pending commands,
releases held notes and logs an error; it never blocks a musical callback waiting
for device I/O. Changing occurrence probability no longer changes gate/velocity
indirectly; use their existing dedicated controls.
