interface GenericJsonEditorProps {
  value: string;
  disabled?: boolean;
  onChange: (next: string) => void;
}

export function GenericJsonEditor({ value, disabled, onChange }: GenericJsonEditorProps) {
  return (
    <textarea
      className="control-textarea"
      value={value}
      disabled={disabled}
      rows={6}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
