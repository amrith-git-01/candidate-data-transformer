import { Plus, Trash2, AlertTriangle } from "lucide-react";

// Each source maps to a fixed output type (and optional normalize). These mirror
// what the projector expects — not user-editable.
const SOURCE_PATH_OPTIONS = [
  { value: "candidate_id", label: "candidate_id", type: "string" },
  { value: "full_name", label: "full_name", type: "string" },
  { value: "emails[0]", label: "emails[0]", type: "string" },
  { value: "phones[0]", label: "phones[0]", type: "string", normalize: "E164" },
  { value: "location.city", label: "location.city", type: "string" },
  { value: "location.region", label: "location.region", type: "string" },
  { value: "location.country", label: "location.country", type: "string" },
  { value: "headline", label: "headline", type: "string" },
  { value: "years_experience", label: "years_experience", type: "number" },
  {
    value: "skills[].name",
    label: "skills[].name",
    type: "string[]",
    normalize: "canonical",
  },
  { value: "links.linkedin", label: "links.linkedin", type: "string" },
  { value: "links.github", label: "links.github", type: "string" },
  { value: "links.portfolio", label: "links.portfolio", type: "string" },
  {
    value: "experience[].company",
    label: "experience[].company",
    type: "string[]",
  },
  {
    value: "experience[].title",
    label: "experience[].title",
    type: "string[]",
  },
  {
    value: "education[].institution",
    label: "education[].institution",
    type: "string[]",
  },
  {
    value: "education[].degree",
    label: "education[].degree",
    type: "string[]",
  },
  { value: "education[].field", label: "education[].field", type: "string[]" },
  {
    value: "education[].end_year",
    label: "education[].end_year",
    type: "number",
  },
  { value: "matched_by", label: "matched_by", type: "string" },
  { value: "overall_confidence", label: "overall_confidence", type: "number" },
];

const SOURCE_META = Object.fromEntries(
  SOURCE_PATH_OPTIONS.map((o) => [o.value, o]),
);

const inputClass =
  "w-full rounded-lg border border-line-soft bg-canvas px-2.5 py-1.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-200";

const inputErrorClass =
  "w-full rounded-lg border border-rose-400 bg-rose-50 px-2.5 py-1.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-rose-200";

const metaClass = "px-1 text-sm text-ink-soft md:text-center";

function emptyField() {
  return {
    path: "",
    from: "",
    type: "string",
    required: false,
    normalize: null,
  };
}

function fieldMetaFromSource(from) {
  const meta = SOURCE_META[from];
  if (!meta) {
    return { type: "string", normalize: null };
  }
  return {
    type: meta.type,
    normalize: meta.normalize ?? null,
  };
}

function countBySource(fields) {
  const counts = new Map();
  for (const f of fields) {
    if (!f.from) continue;
    counts.set(f.from, (counts.get(f.from) ?? 0) + 1);
  }
  return counts;
}

export function hasDuplicateSources(fields) {
  return [...countBySource(fields).values()].some((count) => count > 1);
}

function ReadOnlyMeta({ value }) {
  if (!value) {
    return <span className={`${metaClass} text-ink-soft/40`}>—</span>;
  }
  return <span className={metaClass}>{value}</span>;
}

export default function FieldsBuilder({ fields, onChange }) {
  const sourceCounts = countBySource(fields);

  function updateField(index, patch) {
    const next = fields.map((f, i) => (i === index ? { ...f, ...patch } : f));
    onChange(next);
  }

  function updateSource(index, from) {
    const { type, normalize } = fieldMetaFromSource(from);
    updateField(index, { from, type, normalize });
  }

  function removeField(index) {
    onChange(fields.filter((_, i) => i !== index));
  }

  function addField() {
    onChange([...fields, emptyField()]);
  }

  return (
    <div>
      <p className="mb-3 text-xs text-ink-soft">
        <strong className="text-ink">Output path</strong> is whatever name you
        want in the result — rename freely.{" "}
        <strong className="text-ink">Source</strong> picks a canonical field;
        <strong className="text-ink"> type</strong> and{" "}
        <strong className="text-ink">normalize</strong> are set automatically
        (E164 for phone, canonical for skills). A source with no value resolves
        empty per the &ldquo;On missing field&rdquo; setting above.
      </p>

      {fields.length > 0 && (
        <div className="mb-2 hidden grid-cols-[1fr_1fr_88px_88px_70px_36px] gap-2 px-1 text-xs font-semibold uppercase tracking-wide text-ink-soft md:grid">
          <span>Output path</span>
          <span>Source</span>
          <span>Type</span>
          <span>Normalize</span>
          <span>Required</span>
          <span />
        </div>
      )}

      <div className="space-y-2">
        {fields.map((field, index) => {
          const hasCustomSource =
            field.from &&
            !SOURCE_PATH_OPTIONS.some((o) => o.value === field.from);
          const isDuplicateSource =
            field.from && (sourceCounts.get(field.from) ?? 0) > 1;
          const normalizeLabel = field.normalize ?? null;

          return (
            <div
              key={index}
              className="grid grid-cols-1 gap-2 rounded-lg border border-line-soft bg-white p-2.5 md:grid-cols-[1fr_1fr_88px_88px_70px_36px] md:items-center"
            >
              <input
                type="text"
                value={field.path}
                onChange={(e) => updateField(index, { path: e.target.value })}
                placeholder="output_field"
                className={inputClass}
              />
              <div>
                <select
                  value={field.from ?? ""}
                  onChange={(e) => updateSource(index, e.target.value)}
                  className={isDuplicateSource ? inputErrorClass : inputClass}
                  aria-invalid={isDuplicateSource}
                >
                  <option value="" disabled>
                    Select a canonical field…
                  </option>
                  {hasCustomSource && (
                    <option value={field.from}>
                      {field.from} (unrecognized)
                    </option>
                  )}
                  {SOURCE_PATH_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                {isDuplicateSource && (
                  <p className="mt-1 flex items-center gap-1 text-xs text-rose-600">
                    <AlertTriangle size={12} className="shrink-0" />
                    Source already used by another field
                  </p>
                )}
              </div>
              <ReadOnlyMeta value={field.from ? field.type : null} />
              <ReadOnlyMeta value={normalizeLabel} />
              <label className="flex items-center justify-center gap-1.5 text-xs text-ink-soft md:justify-self-center">
                <input
                  type="checkbox"
                  checked={field.required}
                  onChange={(e) =>
                    updateField(index, { required: e.target.checked })
                  }
                  className="h-4 w-4 rounded border-line-soft text-brand-600 focus:ring-brand-200"
                />
                Required
              </label>
              <button
                type="button"
                onClick={() => removeField(index)}
                aria-label="Remove field"
                className="flex h-8 w-8 items-center justify-center justify-self-end rounded-lg text-ink-soft transition-colors hover:bg-rose-50 hover:text-rose-600 md:justify-self-center"
              >
                <Trash2 size={16} />
              </button>
            </div>
          );
        })}
      </div>

      <button
        type="button"
        onClick={addField}
        className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-dashed border-line-soft px-3 py-2 text-sm font-medium text-brand-700 transition-colors hover:bg-brand-50"
      >
        <Plus size={16} />
        Add field
      </button>
    </div>
  );
}
