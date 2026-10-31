# Generative musical improvements

Implement F07/F08/F10/F11 and M01–M05 from the generative review while preserving
transport fixes. Existing modes gain harmony, recurring motifs and hierarchical
expression. Preset names, controls, public configuration and routes stay stable.

## Acceptance

- Seeded composition sequences replay without modifying process-global randomness.
- Song sections obey rhythm masks and elapsed beats, including live division edits.
- Twelve-bar blues has I/IV/V movement; Minimalist retains static harmony.
- Verse/chorus identities recur; development is confined to the second phrase half.
- One to four voices use non-overlapping registers, chord-aware attacks and bass roots.
- MIDI attacks explicitly retrigger prior owners; old deadlines cannot release replacements.
- Generation runs in bounded process preparation, MIDI writes in an output worker.
- Full backend tests and frontend tests/build pass. Timing must remain below 2 ms
  tick jitter and 10 ms input response; failures remain open, never relabeled passes.
- Reproducible MIDI and event evidence accompany a manual listening/device checklist.

## Defaults and boundaries

No new dashboard controls or dependencies. Seeds are internal constructors/worker
requests and an offline evaluation CLI option. Four beats per bar; existing song
lengths, tempo factors, pauses and step-division contracts remain. Physical MIDI,
Raspberry Pi and listening acceptance require their actual environments.
