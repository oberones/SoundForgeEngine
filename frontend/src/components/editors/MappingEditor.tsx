interface MappingEditorProps {
  value: string;
  disabled?: boolean;
  onChange: (next: string) => void;
}

export function MappingEditor({ value, disabled, onChange }: MappingEditorProps) {
  return (
    <textarea
      className="control-textarea"
      value={value}
      disabled={disabled}
      rows={5}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
