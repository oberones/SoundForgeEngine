interface CollectionEditorProps {
  value: string;
  disabled?: boolean;
  onChange: (next: string) => void;
}

export function CollectionEditor({ value, disabled, onChange }: CollectionEditorProps) {
  return (
    <textarea
      className="control-textarea"
      value={value}
      disabled={disabled}
      rows={4}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
