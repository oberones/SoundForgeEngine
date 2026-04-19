interface ToggleEditorProps {
  value: boolean;
  disabled?: boolean;
  onChange: (next: boolean) => void;
}

export function ToggleEditor({ value, disabled, onChange }: ToggleEditorProps) {
  return (
    <label className="toggle-editor">
      <input type="checkbox" checked={value} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
      <span>{value ? "Enabled" : "Disabled"}</span>
    </label>
  );
}
