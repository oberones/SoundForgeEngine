# Generative Sequencer Engine Review

Review date: **2026-10-31**  
Source revision checked when documenting: `27501378f69499c09aedf77568a90641a0c779c1`  
Status: **Original review snapshot, followed by a 2026-10-31 implementation and validation update below.**

## Summary and evidence boundaries

The engine has substantial defects affecting song progression, rhythmic timing,
and contrapuntal voice ordering. Correct those foundations before adding new
composition features. The largest musical opportunities are harmonic direction,
recognizable motifs, coordinated voices, and phrase-level rhythm and expression.

This document preserves the findings from the read-only source review and its
local Python experiments. Source locations were rechecked while documenting the
review. Relative links identify the relevant files; function names identify the
specific code independently of future line-number changes.

Evidence labels used below:

- **Reproduced:** observed with direct, in-process Python calls during the review.
- **Source-based:** established by inspecting code paths or calculating their
  behavior; no end-to-end playback reproduction is claimed.
- **Measured:** a local elapsed-time observation, not a benchmark distribution or
  measurement of MIDI-device timing.
- **Recommendation:** a proposed improvement whose musical value needs listening
  evaluation; it is not an established defect merely because it is absent.

P1 findings should be addressed first because they break core playback or
composition behavior. P2 findings materially affect musical behavior or control
semantics and should follow. All findings were open in the original review snapshot. See the implementation
update below for current resolution status and remaining acceptance work.

## Defect findings

### F01 — P1: Song sections do not advance with common sequence lengths

**Evidence: Reproduced and source-based.**

In [song.py](../src/song.py), `SongSequencer._check_section_advancement()`
increments the bar count only when `step > 0` and `step % 16 == 0`. The parent
[Sequencer](../src/sequencer.py) supplies a looping pattern position, not an
elapsed-step counter. With the default eight-step sequence, positions are 0–7;
a sixteen-step sequence also never reaches position 16.

**Observed:** after 4,096 calls to `get_next_step_notes(i % 8)`, the song still had
section index `0` and bar count `0`.

**Musical impact:** the song remains in its opening section instead of developing
through its intended form. Longer patterns do not solve the underlying confusion
between pattern position and elapsed musical time.

**Recommended correction:** maintain a musical transport counter independent of
pattern traversal and count bars from elapsed beats. Test complete section and
song progression through the parent sequencer at multiple sequence lengths.

### F02 — P1: The between-song pause becomes permanent silence

**Evidence: Reproduced and source-based.**

In [song.py](../src/song.py), `get_next_step_notes()` calls `start_new_song()` after
five seconds in the between-song state. However, `start_new_song()` immediately
returns while `_between_songs` is true. The automatic path never clears that flag.

**Observed:** after calling `_start_between_songs()` and setting the pause start
time to six seconds earlier, another playback call left `_between_songs == True`
and `_current_pattern is None`.

**Musical impact:** once a song reaches the pause, automatic playback cannot resume.
F01 can mask this separate defect by preventing natural song completion.

**Recommended correction:** clear the pause state as part of the automatic
transition to the next composition. Verify that the pause lasts five seconds and
that the next song starts exactly once, including after natural completion.

### F03 — P1: Fugue generation blocks the timing thread

**Evidence: Source-based call path and illustrative local measurements.**

In [fugue.py](../src/fugue.py), `get_next_step_notes()` can call
`start_new_fugue()`, which synchronously generates a subject and renders and
optimizes the complete score. During ongoing playback, this is reached from the
parent sequencer's clock callback.

**Measured:** timing subject generation plus `render_fugue()` with
`time.perf_counter()` produced the following single-run observations:

| Voices | Local generation time |
| --- | ---: |
| 1 | 0.05 ms |
| 3 | 205.34 ms |
| 4 | 322.71 ms |

These measurements used generated material, not a fixed benchmark corpus. They
are not percentile statistics, live tick-jitter measurements, or Raspberry Pi
performance results.

**Musical impact:** synchronous multi-voice generation can interrupt the timing
loop and cause a gap or timing reset when a new fugue is needed. Work lasting
hundreds of milliseconds on this path conflicts with the
[constitution](../.specify/memory/constitution.md)'s under-2-ms tick-jitter target
and prohibition on heavy work in timing-sensitive paths.

**Recommended correction:** prepare upcoming scores off the timing path and hand
off completed scores at a musical boundary. Verify timing under generation load;
moving CPU-heavy Python work to a thread alone does not establish that the timing
budget is met.

### F04 — P1: The fugue optimizer penalizes correctly ordered voices

**Evidence: Reproduced and source-based.**

In [fugue.py](../src/fugue.py), `_default_ranges_abs` orders voices as soprano,
alto, tenor, and bass. However, `_score_counterpoint()` adds a crossing penalty
when an earlier-index voice is above a later-index voice (`a > b`). This is the
opposite of the declared register order.

**Observed:** a two-voice score containing simultaneous two-beat notes at MIDI
pitches `(76, 67)` received a crossing cost of `7.0`. Reversing the pitches to
`(67, 76)` received a crossing cost of `0.0`.

**Musical impact:** optimization rewards movement toward incorrect voice ordering,
working against the intended soprano/alto/tenor/bass separation.

**Recommended correction:** make the crossing comparison agree with the declared
voice order. Test ordered and crossed pairs and verify the final optimized score,
including custom ranges.

### F05 — P1: Playback timing disagrees with configured note division

**Evidence: Source-based across modes; standard-mode gate error reproduced.**

The parent [Sequencer](../src/sequencer.py) changes its step frequency according
to `note_division`. In contrast:

- [FugueSequencer.get_next_step_notes()](../src/fugue.py) advances exactly
  `0.25` quarter-note beats per call and converts note durations using BPM alone.
- [SongSequencer._generate_voice_note()](../src/song.py) calculates durations
  as a fraction of a sixteenth note regardless of the parent's division.
- Standard-mode `_generate_step_note()` omits the half/whole-note beat multiplier
  when calculating gate duration, even though clock timing applies it.

The working [config.yaml](../config.yaml) selects `note_division: quarter`.
In fugue mode this advances score time at one quarter of the expected rate:
onset spacing is generally four times the intended spacing while emitted note
durations retain their BPM-based lengths. F06 separately affects the initial
interval.

**Observed standard-mode example:** at 120 BPM with whole-note division, density
and step probability of `1.0`, an active step, base gate `0.8`, and gate variation
`0.0`, the step interval was `2.0` seconds but the generated gate was `0.4` seconds.
An 80% gate for that step should be `1.6` seconds.

**Musical impact:** unintended gaps and short articulation; score rhythm and
playback tempo no longer agree.

**Recommended correction:** establish one beat-based timing contract for all
modes, separating transport resolution from pattern traversal and articulation.
Verify onset spacing and gate duration for whole, half, quarter, eighth, and
sixteenth divisions and after live tempo/division changes.

### F06 — P1: Fugue playback advances time before emitting the initial event

**Evidence: Reproduced and source-based.**

In [fugue.py](../src/fugue.py), `get_next_step_notes()` increments
`_fugue_musical_time` before checking which notes are due. New scores start with
musical time and each voice's next-note time both set to zero.

**Observed:** a manually supplied voice with two consecutive quarter notes emitted
on zero-based calls `0` and `3`, rather than `0` and `4` at sixteenth-note resolution.

**Musical impact:** the initial interval is shortened by one step and can overlap
the first two notes even when the score does not request overlap.

**Recommended correction:** process events at the current musical position before
advancing time. Cover initial notes, initial rests, multiple voices, and subsequent
onsets with exact beat-position assertions.

### F07 — P2: New fugues repeat random material and reset shared randomness

**Evidence: Reproduced for subjects; source-based for global RNG coupling.**

In [fugue.py](../src/fugue.py), the engine chooses `_seed` once during construction.
Every `generate_subject()` call then runs `random.seed(self._seed)`, resetting
Python's process-wide random generator.

**Observed:** two subject-generation calls on the same engine with unchanged
parameters produced identical subjects. The direct reproduction compared subjects,
not full MIDI recordings of successive fugues.

**Musical impact:** new compositions can repeat the same material unintentionally.
Resetting the shared RNG also couples fugue generation to other random behavior,
including song generation and mutation.

**Recommended correction:** use an instance-owned RNG and distinguish intentional
replay from generation of a new composition. Preserve explicit seeds for regression
tests and reproducible performances without resetting unrelated random streams.

### F08 — P2: Song section rhythm presets do not affect playback

**Evidence: Source-based.**

In [song.py](../src/song.py), `_apply_section_settings()` writes
`song_step_pattern`. A source search found that assignment but no consumer of
the value. Song playback also bypasses the standard sequencer's pattern gating.

**Musical impact:** section settings such as `sparse`, `syncopated`, and
`every_other` do not produce their requested rhythmic patterns. Section contrast
is weaker than the presets imply.

**Recommended correction:** apply section rhythm patterns in the song-generation
path with explicit behavior for sections without an override. Test emitted onset
positions, not merely whether the preset name was written to state.

### F09 — P2: Quantized scale changes follow pattern position instead of bars

**Evidence: Source-based.**

In [sequencer.py](../src/sequencer.py), `_advance_step()` treats
`_current_step == 0` as a bar boundary and applies pending scale changes there.
Pattern position depends on sequence length and forward, backward, ping-pong,
or random traversal; it is not an independent measure of elapsed bars.

**Musical impact:** harmonic-change timing varies with traversal and can occur at
irregular times in random mode. A pattern wrap need not align with a musical bar.

**Recommended correction:** schedule quantized changes against the same musical
transport used for F01 and F05. Verify consistent bar-boundary behavior across
sequence lengths and traversal directions.

### F10 — P2: Overlapping same-pitch notes have no ownership model

**Evidence: Source-based; receiver-dependent audible impact was not tested.**

In [main.py](../src/main.py), `handle_note_event()` sends generated voices on the
configured output channel. `NoteScheduler.schedule_note_off()` independently
schedules each note-off using only note, channel, and deadline. It does not track
which overlapping voice or retrigger owns a sounding note.

**Musical impact:** an earlier note-off can shorten a later overlapping note of
the same pitch and channel, depending on the receiving instrument's behavior.
Independent polyphonic voices can therefore interfere with one another.

The same scheduler uses `time.time()` for deadlines, unlike the sequencer's
monotonic clock. System wall-clock changes can shift note-off timing; this was
identified in source, not reproduced with a system-clock change.

**Recommended correction:** define same-pitch overlap and retrigger semantics and
implement ownership accordingly, or support independent voice channels where
appropriate. Use monotonic note-off deadlines. Validate the message sequence with
a fake MIDI sink, then qualify audible behavior on the intended receiving synth.

### F11 — P2: Melodic interval probabilities differ from the documented intent

**Evidence: Source-based probability calculation.**

In [fugue.py](../src/fugue.py), `generate_subject()` uses one random draw for the
60% step branch and a second draw for the small-leap branch. The comments describe
60% steps, 30% small leaps, and 10% larger leaps. Actual branch probabilities are:

| Interval category | Documented | Actual branch probability |
| --- | ---: | ---: |
| Steps | 60% | 60% |
| Small leaps | 30% | 40% × 30% = 12% |
| Larger leaps | 10% | 40% × 70% = 28% |

These are branch-selection probabilities before later direction changes, range
clamping, rests, or other processing; they are not measured output-note statistics.

**Musical impact:** large leaps are selected substantially more often than intended,
making subjects jumpier than the documented melodic design.

**Recommended correction:** use a single draw with cumulative thresholds or an
explicit weighted choice. Test branch boundaries deterministically and separately
inspect the resulting melodic interval distribution.

## Musical improvement opportunities

These are recommendations, not claims that a particular style is universally
better. Validate them through reproducible listening comparisons after correcting
the playback defects.

### M01 — Give song mode harmonic direction

[Song mode](../src/song.py) reuses four short scale-degree patterns with random
adjacent-degree changes. Its section labels and lengths do not provide a chord
timeline; in particular, the `12-Bar Blues` preset does not implement the associated
harmonic progression.

Introduce explicit harmonic movement, bass roots, chord-aware strong beats, and
phrase-ending cadences. Preserve modal or static-harmony options where those are
the intended aesthetic. Evaluate whether listeners can hear departure, tension,
and return across a phrase and across the complete form.

### M02 — Develop recognizable motifs across sections

Retain melodic and rhythmic identities for verses and choruses. Apply bounded
changes at phrase boundaries: sequence, rhythmic displacement, ornamentation,
or alternate endings. The current per-note variation supplies variety without
explicitly developing a theme.

Evaluate motif recurrence and whether a returning chorus remains recognizable
while avoiding exact repetition throughout the piece.

### M03 — Coordinate voices around harmonic intent

Song voices largely choose notes independently. The
[fugue optimizer](../src/fugue.py)'s pitch proposals include semitone neighbors
without an explicit tonal constraint. Local interval improvements alone do not
guarantee coherent harmony or melodic resolution.

Use shared harmony, stable register roles, voice-leading costs, and deliberate
handling of non-chord tones. Keep chromaticism available with preparation and
resolution rather than indiscriminately forcing every pitch into a scale.
Evaluate strong-beat harmony, voice independence, register crossings, and the
behavior of dissonances across time.

### M04 — Make rhythm and expression hierarchical

In [standard mode](../src/sequencer.py), occurrence probability also influences
velocity and gate length. In song mode, voices have essentially uniform short
durations at a given tempo and gate setting. These mechanisms do not explicitly
model meter accents or phrase shape.

Separate occurrence probability, metrical accents, articulation, and phrase-level
dynamics. Add sustained accompaniment, rhythmic answers, phrase-end space, and
coherent accent patterns. Evaluate groove and phrase shape at equal tempo and
comparable density so that louder or denser output is not mistaken for improvement.

### M05 — Make musical evaluation reproducible

Create fixed-seed MIDI fixtures and event-level checks for section duration,
cadence placement, register crossings, unresolved strong-beat dissonance, and
motif recurrence. Use isolated random streams as recommended in F07.

Pair these checks with listening comparisons using the same synth, patches, tempo,
and playback conditions. A lower counterpoint score alone does not establish
better music, especially while the scorer itself contains defects such as F04.

## Validation record and recommended follow-up

### Evidence available from the review

| Check | Result and limit |
| --- | --- |
| Targeted sequencer, song, fugue, and mutation tests | **PASS:** 87 tests; command below exited successfully. |
| Full backend suite | **INCOMPLETE at reporting time:** started, but no completed result was available for the review. This is not a pass. |
| Direct Python experiments | Reproduced F01, F02, F04, the standard gate case in F05, F06, and repeated subjects in F07. |
| Fugue generation timing | Single local observations recorded under F03; no timing-budget certification. |
| MIDI hardware and synth behavior | **NOT VALIDATED.** |
| Listening quality | **NOT VALIDATED.** Musical recommendations require listening evaluation. |

Commands used from the repository root, with Python inside the project virtual
environment:

```sh
.venv/bin/pytest tests/test_sequencer.py tests/test_song_mode.py tests/test_fugue.py tests/test_mutation.py -q
.venv/bin/pytest tests -q
```

Direct experiments used `PYTHONPATH=src .venv/bin/python`, reset the global state
before state-dependent scenarios, and exercised objects in process without MIDI
hardware. The observations above preserve the review results; no permanent
reproduction scripts or raw-log artifacts were added with this document.

### Recommended correction order and regression coverage

1. **Repair transport and song lifecycle:** address F01, F02, F05, F06, and F09
   together around consistent beat positions. Drive the real parent sequencer
   through complete sections and songs; cover sequence lengths 8 and 16, all note
   divisions, traversal modes, tempo changes, and the between-song transition.
2. **Protect timing:** address F03 and the monotonic deadline portion of F10.
   Measure callback execution and tick jitter during three- and four-voice score
   preparation and handoff. Preserve under-2-ms tick jitter and sub-10-ms input
   response under the project's supported performance conditions.
3. **Correct voice behavior:** address F04 and F10's overlap semantics. Assert
   register ordering before and after optimization and capture note-on/off streams
   for coincident pitches, retriggers, and independent voices. Keep fake-sink tests
   distinct from acceptance on a physical synth.
4. **Restore generative intent:** address F07, F08, and F11. Verify explicit-seed
   replay, new-composition generation, RNG isolation, effective section rhythms,
   and intended interval branch probabilities.
5. **Develop and evaluate musical features:** pursue M01–M05 with fixed reference
   performances and listening comparisons after the foundational corrections.

The passing targeted tests do not invalidate these findings: the direct
reproductions expose interactions those tests did not catch. Future behavior
changes require regression tests and appropriate performance validation under the
[project constitution](../.specify/memory/constitution.md). Any new controls must
keep dashboard, API, CLI, and hardware semantics aligned with the
[semantic action reference](reference/SEMANTIC_ACTIONS_REFERENCE.md).

This documentation addition changes no engine behavior or public interface and
does not rerun or upgrade the review's runtime validation claims.


## Implementation update — 2026-10-31

The original observations above are retained as historical evidence. This update
covers F01–F06 and the shared-transport defect F09; it does not close the other P2
findings or the musical improvement recommendations.

| Finding | Current implementation status |
| --- | --- |
| F01 | Fixed: song sections use elapsed quarter-note beats, independently of looping pattern positions. |
| F02 | Fixed: the five-second monotonic pause ends once, and playback resumes on the first eligible pattern step. |
| F03 | Blocking generation path removed: spawned worker plus coordinator prepares and publishes immutable scores. **Timing-budget acceptance remains open**, as detailed below. |
| F04 | Fixed: crossing costs agree with soprano-to-bass ordering, including custom ranges in that order. |
| F05 | Fixed: the clock stays at actual BPM; standard/song gates follow division, while fugue events follow their score beats. |
| F06 | Fixed: beat-zero events emit before elapsed score time advances; final notes and rests finish before the rest period starts. |
| F09 | Fixed: pending scale changes apply before events at elapsed four-beat bar boundaries. |

### Playback and lifecycle contract

- The clock remains at 24 ticks per quarter note. Whole/half/quarter/eighth/sixteenth
  pattern steps take 96/48/24/12/6 ticks. BPM changes preserve beat position;
  division edits latch at the next pattern step boundary. Swing retains its
  existing clock behavior. Smooth tempo transitions also govern new note gates.
- Song sections count four beats per bar. Forced section changes establish a new
  origin. Natural completion restores base settings and starts the five-second
  pause. The next song emits at the first pattern step after that pause expires.
- Fugue onsets run on clock ticks independently of note division. Non-grid onsets
  emit on the first tick at or after their score position. Durations convert to
  seconds using BPM at note emission; already emitted note-off deadlines are not
  rescaled during tempo changes. Same-pitch note ownership remains F10 follow-up.
- A coordinator owns one spawned process, at most one in-flight request, and one
  ready score. Rendering, optimization, onset grouping, submission, deserialization,
  error logging, and five-second retry backoff run outside timing callbacks.
  Completed scores are adopted by reference at a bar boundary after the ten-second
  fugue pause. When preparation is late, playback stays silent and the coordinator
  logs `fugue_preparation_waiting`; no synchronous fallback exists.
- Composition changes invalidate prepared results by snapshot and epoch. The current
  composition can finish; leaving fugue mode abandons it. Stop joins preparation
  outside the clock thread. Restart preserves musical position without emitting the
  initial event again. No dependencies, public configuration keys, HTTP routes, or
  CLI commands were added.

### Automated verification

Regression coverage is in
[`test_transport_regressions.py`](../tests/test_transport_regressions.py) and
[`test_fugue_preparation.py`](../tests/test_fugue_preparation.py). Existing fugue
playback tests now consume fixed prepared scores; the older scale-change test now
advances elapsed bars instead of assuming pattern wrap means bar boundary.

Eight regression cases failed before implementation: stuck song, stuck pause,
whole-note gate, crossing cost, and scale quantization across four traversals.
The final coverage additionally exercises complete songs at lengths 8/16 and all
five divisions, live tempo/division changes, forced sections, initial rests,
polyphonic and off-grid onsets, final rests, delayed/stale preparation, retries,
shutdown, bounded lookahead, register ordering after optimization, and restart.

Frontend verification: **PASS**, three Vitest tests and the TypeScript/Vite
production build. Backend results and timing measurements are recorded below.

### Performance qualification and remaining gate

[`tools/check_generative_timing.py`](../tools/check_generative_timing.py) measures
absolute clock deadline error, callback duration, and semantic button-dispatch
latency using a fake note sink. It repeatedly shortens compositions and removes
pauses **only in the benchmark** to exercise preparation and handoff under load.
The benchmark exits nonzero if either latency budget is missed or repeated
handoffs do not occur. It does not test physical input, MIDI delivery, or audible
response.

Commands (all Python runs in the project virtual environment):

```sh
.venv/bin/pytest tests -q -o addopts=''
(cd frontend && npm test && npm run build)
.venv/bin/python tools/check_generative_timing.py --seconds 12
.venv/bin/python tools/check_generative_timing.py --seconds 12 --baseline
```

The initial local load measurement and generation-disabled comparison are retained
as [`timing-load-initial.json`](validation/generative-engine/timing-load-initial.json)
and [`timing-baseline.json`](validation/generative-engine/timing-baseline.json).
Both used macOS 26.6.2 arm64, Python 3.14.6, 200 BPM, 24 PPQ, zero swing, and
12 seconds per voice count. The initial load run overlapped backend validation;
the final load run below was performed without a concurrent test command.

**Performance exception:** the under-2-ms clock-jitter gate is not satisfied on this
local host. Even with generation disabled, maximum deadline errors were 9.735 ms
and 6.913 ms (three/four-voice parameter settings); median errors were about 1.96 ms.
This establishes that removing generation alone is insufficient. The existing
sleep-based clock and host scheduling need separate qualification and potentially
clock-wait tuning. This is not evidence that every outlier is caused by the OS,
nor a Raspberry Pi acceptance result. The engine maintainers own follow-up:
measure on supported deployment hardware under representative input/MIDI load,
address clock scheduling as indicated, and close F03 performance acceptance only
after both timing targets pass. No timing threshold was relaxed and no busy-wait
or platform-priority policy was introduced to mask this failure.

Physical MIDI/synth behavior, native device input latency, Raspberry Pi timing,
and listening acceptance remain **NOT VALIDATED**.


Final isolated load results are retained in
[`timing-load-final.json`](validation/generative-engine/timing-load-final.json):

| Measurement | Three voices | Four voices |
| --- | ---: | ---: |
| Prepared-score handoffs | 9 | 9 |
| Clock callbacks sampled | 961 | 962 |
| Callback p99 / maximum | 0.178 / 0.502 ms | 0.135 / 0.745 ms |
| Deadline error p99 / maximum | 4.151 / 15.208 ms | 3.113 / 8.063 ms |
| Button dispatch p99 / maximum | 0.417 / 2.127 ms | 0.713 / 1.159 ms |
| Under-2-ms deadline-error gate | **FAIL** | **FAIL** |
| Sub-10-ms semantic dispatch gate | **PASS locally** | **PASS locally** |

The measurements confirm short playback callbacks and repeated process-prepared
handoffs in this run, while explicitly leaving overall clock-jitter acceptance open.


Final backend verification: **368 passed in 13.55 seconds**, with no skips or
warnings, using local socket access for live-server tests. The first sandbox run
could not bind localhost and skipped seven server tests; that run was superseded
by the complete rerun. Raw output:
[`backend-tests.txt`](validation/generative-engine/backend-tests.txt).

## Musical improvements implementation — 2026-10-31

This follow-up implements the remaining F07/F08/F10/F11 corrections and M01–M05
capabilities. It preserves the historical review and earlier transport repair record.
The implementation specification is in
[`specs/002-generative-improvements`](../specs/002-generative-improvements/spec.md).

- **F07/F11:** fugue and song composition use private seeded streams. Worker requests
  carry composition seeds; retries retain their identity and adoption advances the
  upcoming seed. Fugue interval branches now use cumulative 60/30/10 thresholds.
- **F08:** song playback consumes the shared rhythm masks using elapsed section-step
  counts, resets them at section boundaries, and uses `all_on` without an override.
- **F10:** a bounded output worker serializes attacks and monotonic releases. Same-
  channel/pitch attacks explicitly release the previous owner before retriggering;
  replacement deadlines invalidate old releases. Broadcast channels expand before
  ownership; shutdown flushes active notes. Overflow logs and performs a worker-side
  panic rather than blocking the musical callback.
- **M01/M02:** immutable song tables include diatonic chord timelines, dominant-seventh
  twelve-bar blues, tonic-drone Minimalist, separate section motifs, returning first
  halves, and bounded sequence/displacement/ornamentation in developed second halves.
  Outro endings resolve to tonic. Existing preset lengths and tempo factors remain.
- **M03/M04:** song voices have descending, disjoint registers, chord-aware notes,
  bass roots, sustained inner voices, answering rhythms, metrical accents and phrase-
  ending space. Fugue optimization adds chromatic preparation/resolution costs and
  rejects candidates that worsen crossing or tonal costs. This is a constrained
  improvement, not a guarantee of zero fugue crossings or dissonances. Standard-mode
  probability no longer indirectly scales velocity or gate duration.
- **M05:** the evaluation tool exports fixed-seed events, MIDI, metrics, harmony/motif
  metadata and source hashes. Archived-source baseline and current performances are
  retained alongside density/velocity-matched diagnostic pairs. No dependency or
  public route, configuration key, dashboard control or hardware action was added.

Song generation uses the existing bounded process-coordinator mechanism. Playback
reads immutable tables. Scale/root/voice changes prepare replacements and adopt them
at elapsed bar boundaries; late work defers adoption. Pattern division remains live
at its existing step boundary. Each song step consumes prepared attacks crossed
since the previous callback, keeping the latest attack per voice. This preserves
playback when a live division change leaves steps offset from the prepared grid.
Masked steps discard their attacks; section transitions reset the attack cursor.
Lookup is bounded to 16 quarter-beat rows (the longest supported division), and
melody gates use the newly active division, clipped at the section boundary.
Failed preparation retries with the same seed after
five seconds; there is no synchronous callback fallback. Timing/input paths queue
MIDI work instead of writing to the device.

### Final automated evidence

| Check | Result |
| --- | --- |
| Full backend suite, with localhost access | **PASS: 411 tests in 14.05 seconds**, no skips or warnings. |
| Frontend Vitest | **PASS: 3 tests.** |
| TypeScript/Vite production build | **PASS.** |
| Playwright command | **3 skipped placeholders; no browser acceptance coverage.** |
| Exported MIDI decode/ownership audit | **PASS: 32 files**, balanced attacks/releases and no unowned overlapping pitch attacks. |
| Diff whitespace check | **PASS.** |

The first full sandbox run skipped localhost tests; the completed run above
supersedes it. Backend output is retained as
[`backend-tests.txt`](validation/generative-engine/improvements/backend-tests.txt).
New tests cover seed isolation/replay/advancement, interval thresholds, all six song
presets with one through four voices, extreme MIDI roots, motif recurrence, cadence
placement, masks, stale/late preparation, live scale adoption, probability-independent
expression, monotonic retrigger ownership, broadcast, overload, shutdown, absolute
clock recovery and MIDI export. Existing transport and preparation tests continue
to cover division/tempo changes, full-song transitions and worker retry/lifecycle.

The seed-1729 event audit observed zero song register crossings. Fugue crossing
observations fell from 47 to 21 for three voices and from 45 to 16 for four voices
in these fixtures; those are event-level observations, not a complete proof of
voice ordering or musical quality. Raw song performances are substantially sparser;
the comparison directory supplies explicit density-matched diagnostic variants.

### Clock tuning and open acceptance

The clock now uses absolute deadlines without accumulating wakeup delay into later
deadlines. Severe lateness rebases the next wall-clock deadline without bursting
missed callbacks or advancing musical position artificially. In tuned operation,
sleeps are capped at 1 ms before a final spin capped at 0.5 ms. No elevated process
priority or relaxed timing threshold is used.

Sleep-only baseline deadline-error medians remained around 2 ms. Final tuned
baseline medians were approximately 0.0007–0.0010 ms, with parent CPU around
7.1–7.4% versus approximately 4% sleep-only. Outliers persist; lower median error
does **not** satisfy the hard maximum-jitter requirement.

Final isolated load measurement: macOS 26.6.2 arm64, Python 3.14.6, 200 BPM,
24 PPQ, zero swing, 12 seconds per mode/voice setting. The fake MIDI sink measures
queued output delivery, and semantic triggers include a raw note and the production
note callback. Generation and pauses are shortened only in the benchmark.

| Mode / voices | Handoffs | Max callback | Max deadline error | Max semantic dispatch | Max MIDI queue delay | Parent CPU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Fugue / 3 | 9 | 0.305 ms | 3.660 ms | 0.608 ms | 4.174 ms | 6.00% |
| Fugue / 4 | 9 | 0.294 ms | 2.045 ms | 0.831 ms | 1.331 ms | 5.62% |
| Song / 3 | 13 | 0.770 ms | 3.051 ms | 1.450 ms | 1.181 ms | 8.68% |
| Song / 4 | 13 | 0.928 ms | 2.629 ms | 0.660 ms | 1.537 ms | 8.68% |

No MIDI commands were dropped. Even the conservative sum of maximum semantic
processing and maximum queue delay remains below 10 ms locally. **All four runs
still FAIL the under-2-ms deadline-error gate** and the timing tool exits nonzero.
F03 performance acceptance remains open. Parent CPU excludes spawned renderer CPU;
these are short local observations, not deployment certification.

Raw baseline, initial tuning and final load records are under
[`improvements/`](validation/generative-engine/improvements/). The
[acceptance worksheet](validation/generative-engine/improvements/ACCEPTANCE.md)
provides reproduction instructions and listening/device gates. Physical MIDI,
native device response, Raspberry Pi timing and listening quality remain **NOT
VALIDATED**. Maintainers must qualify these on the intended hardware and close the
unchanged timing gate before claiming performance acceptance.

### Live division playback follow-up

Changing a running song from sixteenths to quarters at beat 0.25 previously
sampled only odd prepared rows and silenced the initial arrangements. Playback now
consumes crossed attacks once, retaining the latest per voice at each live step.
The regression coverage includes eighth/quarter/half/whole changes at four step
phases with three/four voices through intro, verse and chorus, a return to
sixteenths, muted steps, forced sections and off-grid section origins.

- Before the fix, 18 of the initial 19 regression cases failed. The final expanded
  regression file passes all 36 cases.
- Full backend suite with localhost access: **447 passed in 14.20 seconds**, no
  skips. Frontend: **3 tests passed**, TypeScript check and production build passed.
- `.venv/bin/python tools/check_generative_timing.py --seconds 6` remains **FAIL**.
  Song callback maxima were 0.249/3.455 ms for three/four voices; deadline-error
  maxima were 2.647/7.048 ms. The four-voice conservative dispatch-plus-queue maximum
  was 10.064 ms; no MIDI commands were dropped. This short local run overlapped
  other automated checks and does not establish performance acceptance or causality.
  F03 and device qualification remain open. Raw results:
  [`live-division-timing.json`](validation/generative-engine/live-division-timing.json).
