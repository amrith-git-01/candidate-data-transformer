import SegmentedControl from "./SegmentedControl";

const CONFIG_PRESETS = {
  default: {
    label: "Default",
    description: "Full canonical schema with provenance and confidence",
  },
  custom: {
    label: "Custom",
    description: "Flattened projection for downstream systems",
  },
};

function presetFor(name) {
  if (CONFIG_PRESETS[name]) return CONFIG_PRESETS[name];
  return {
    label: name.charAt(0).toUpperCase() + name.slice(1),
    description: null,
  };
}

export default function ConfigSelector({ options, value, onChange }) {
  const active = presetFor(value);
  const segments = options.map((name) => ({
    value: name,
    label: presetFor(name).label,
  }));

  return (
    <div className="flex flex-col items-end gap-1.5">
      <SegmentedControl options={segments} value={value} onChange={onChange} />
      {active.description && (
        <p className="max-w-xs text-right text-xs leading-snug text-ink-soft">
          {active.description}
        </p>
      )}
    </div>
  );
}
