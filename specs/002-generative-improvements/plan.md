# Implementation and validation plan

1. Isolate composition RNGs and fix cumulative interval probabilities. Preserve seed
   through retries and advance it only after adoption; reject stale worker output.
2. Prepare immutable song tables using the existing bounded process coordinator.
   Share rhythm masks; apply them per elapsed section step. Use diatonic progressions,
   explicit dominant-seventh blues, modal drone, distinct section motifs, bounded
   second-half transformations and disjoint voice registers. Rebuild active scale/root/
   voice edits in the worker and adopt at an elapsed bar boundary.
3. Constrain fugue optimization by register and tonal preparation/resolution costs.
   Separate standard-mode occurrence from metrical accents and gate variation.
4. Serialize attacks/releases through a bounded output queue. Expand broadcast channels,
   replace active deadlines on retrigger, panic on overflow, and flush on shutdown.
5. Use absolute clock deadlines; test sleep-only and bounded 0.5 ms final spinning.
   Record CPU, deadline error, callbacks, semantic dispatch and output queue latency.
6. Test deterministic musical properties, worker lifecycle, clock recovery and MIDI
   message ordering. Run full backend/frontend checks. Export archived-source baseline
   and current fixtures; preserve provenance and distinguish listening from metrics.

Quality: document new/changed contracts, keep immutable worker inputs and bounded
callback work, add behavior-level tests, and add no runtime dependencies.

Export follow-up: retain voice identity on emitted song events and have the evidence
exporter consume those events. Preserve the existing playback tuple API and exported
JSON schema, including unknown voices for legacy source. Cover crossed-row attacks,
latest-per-voice selection, muted/empty steps, and the full documented export with
regression tests. Keep the 16-row scan and four-voice bound, measure local emission
cost against the 2 ms tick budget, and run backend tests and the frontend build.

Performance exception: host scheduling may still violate the existing hard gate.
Record all outliers and leave acceptance open. Maintainers must qualify supported
Pi hardware with actual input/MIDI load; no priority escalation or threshold change.
