import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LiveControlPanel } from "../../src/domains/live-control/LiveControlPanel";

describe("LiveControlPanel", () => {
  it("renders the curated live controls", () => {
    render(
      <LiveControlPanel
        controls={[
          {
            id: "sequencer__bpm",
            path: "sequencer.bpm",
            control_kind: "scalar",
            label: "BPM",
            description: "Tempo",
            value_type: "float",
            current_value: 110,
            default_value: 110,
            constraints: {},
            availability: "available",
            persist_behavior: "persistable",
            revision: "r1",
            dirty_state: "clean"
          }
        ]}
        snapshot={{
          revision: "r1",
          captured_at: new Date().toISOString(),
          status: "running",
          config_values: { sequencer: { bpm: 110 } },
          state_values: {},
          changed_paths: [],
          messages: []
        }}
        externalChanges={[]}
        onSubmit={vi.fn(async () => ({
          success: true,
          message: "ok",
          applied_to_state: true,
          revision: "r2",
          persisted: false
        }))}
      />
    );

    expect(screen.getByText("Performance Controls")).toBeInTheDocument();
    expect(screen.getByText("BPM")).toBeInTheDocument();
  });
});
