import type { ControlDefinition } from "../../services/types";

interface EnumEditorProps {
  control: ControlDefinition;
  value: string;
  disabled?: boolean;
  onChange: (next: string) => void;
}

export function EnumEditor({ control, value, disabled, onChange }: EnumEditorProps) {
  const options = Array.isArray(control.constraints.enum) ? (control.constraints.enum as string[]) : [];
  return (
    <select className="control-input" value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)}>
      {options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}
