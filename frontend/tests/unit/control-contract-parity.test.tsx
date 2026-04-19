import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ActionCenter } from "../../src/domains/actions/ActionCenter";

describe("ActionCenter", () => {
  it("renders action definitions from the shared contract", () => {
    render(
      <ActionCenter
        actions={[
          {
            id: "trigger_step",
            label: "Trigger Step",
            description: "Advance once",
            availability: "available"
          }
        ]}
        snapshot={{
          revision: "r4",
          captured_at: new Date().toISOString(),
          status: "running",
          config_values: {},
          state_values: {},
          changed_paths: [],
          messages: []
        }}
        feedbackState={{ state: "idle" }}
        onInvoke={vi.fn(async () => ({ message: "ok", revision: "r5" }))}
      />
    );

    expect(screen.getByText("Semantic Workflows")).toBeInTheDocument();
    expect(screen.getByText("Trigger Step")).toBeInTheDocument();
  });
});
