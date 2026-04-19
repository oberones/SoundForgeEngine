import type { ControlDefinition } from "../../services/types";

interface ScalarEditorProps {
  control: ControlDefinition;
  value: string;
  disabled?: boolean;
  onChange: (next: string) => void;
}

export function ScalarEditor({ control, value, disabled, onChange }: ScalarEditorProps) {
  const numeric = control.value_type === "integer" || control.value_type === "float" || control.value_type === "number";

  return (
    <input
      className="control-input"
      type={numeric ? "number" : "text"}
      value={value}
      disabled={disabled}
      min={typeof control.constraints.minimum === "number" ? control.constraints.minimum : undefined}
      max={typeof control.constraints.maximum === "number" ? control.constraints.maximum : undefined}
      step={control.value_type === "integer" ? 1 : "any"}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
