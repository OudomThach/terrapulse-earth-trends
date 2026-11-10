import { useMeta } from '../meta'

/** Variables grouped by type in a native select. */
export function VariableSelect({ value, onChange, label }: { value: string; onChange: (code: string) => void; label: string }) {
  const { meta } = useMeta()
  return (
    <label className="field">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {meta.groups.map((g) => (
          <optgroup key={g} label={g}>
            {meta.variables.filter((v) => v.group === g).map((v) => <option key={v.code} value={v.code}>{v.name}</option>)}
          </optgroup>
        ))}
      </select>
    </label>
  )
}
