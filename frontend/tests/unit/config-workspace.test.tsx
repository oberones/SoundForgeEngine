import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ConfigurationWorkspace } from "../../src/domains/configuration/ConfigurationWorkspace";

describe("ConfigurationWorkspace", () => {
  it("renders domain tabs and control labels", () => {
    render(
      <ConfigurationWorkspace
        domains={[
          {
            id: "sequencer",
            title: "Sequencer",
            description: "Core timing",
            sort_order: 10,
            controls: [
              {
                id: "sequencer__direction_pattern",
                path: "sequencer.direction_pattern",
                control_kind: "enum",
                label: "Direction Pattern",
                description: "Direction",
                value_type: "string",
                current_value: "forward",
                default_value: "forward",
                constraints: { enum: ["forward", "backward"] },
                availability: "available",
                persist_behavior: "persistable",
                revision: "r1",
                dirty_state: "clean"
              }
            ]
          }
        ]}
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

    expect(screen.getByRole("tab", { name: "Sequencer" })).toBeInTheDocument();
    expect(screen.getByText("Direction Pattern")).toBeInTheDocument();
  });
});
