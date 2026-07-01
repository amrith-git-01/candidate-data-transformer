import { Plus, Trash2, AlertTriangle } from "lucide-react";

const TYPE_OPTIONS = ["string", "string[]", "number", "object", "null"];

// Mirrors src/project/projector.py::_apply_normalize — E164 only ever does
// anything for a scalar string (phone-like value), and "canonical" (skill
// name normalization) only ever does anything for a string or string[].
// Anything else is a silent no-op on the backend, so we don't offer it here.
function normalizeOptionsFor(type) {
  if (type === "string")
    return [
      { value: "", label: "None" },
      { value: "E164", label: "E164" },
      { value: "canonical", label: "Canonical" },
    ];
  if (type === "string[]")
    return [
      { value: "", label: "None" },
      { value: "canonical", label: "Canonical" },
    ];
  return [{ value: "", label: "None" }];
}

// The only valid values for "source" — real paths into CanonicalRecord (see
// src/models.py). This isn't a free-rename field: it's what gets *read*,
// so it has to be one of these, unlike "Output path" which can be anything.
const SOURCE_PATH_OPTIONS = [
  { value: "candidate_id", label: "candidate_id" },
  { value: "full_name", label: "full_name" },
  { value: "emails[0]", label: "emails[0]" },
  { value: "phones[0]", label: "phones[0]" },
  { value: "location.city", label: "location.city" },
  { value: "location.region", label: "location.region" },
  { value: "location.country", label: "location.country" },
  { value: "headline", label: "headline" },
  { value: "years_experience", label: "years_experience" },
  { value: "skills[].name", label: "skills[].name" },
  { value: "links.linkedin", label: "links.linkedin" },
  { value: "links.github", label: "links.github" },
  { value: "links.portfolio", label: "links.portfolio" },
  { value: "experience[].company", label: "experience[].company" },
  { value: "experience[].title", label: "experience[].title" },
  { value: "education[].institution", label: "education[].institution" },
  { value: "education[].degree", label: "education[].degree" },
  { value: "education[].field", label: "education[].field" },
  { value: "education[].end_year", label: "education[].end_year" },
  { value: "matched_by", label: "matched_by" },
  { value: "overall_confidence", label: "overall_confidence" },
];

const inputClass =
  "w-full rounded-lg border border-line-soft bg-canvas px-2.5 py-1.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-200";

const inputErrorClass =
  "w-full rounded-lg border border-rose-400 bg-rose-50 px-2.5 py-1.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-rose-200";

function emptyField() {
  return {
    path: "",
    from: "",
    type: "string",
    required: false,
    normalize: null,
  };
}

// The projector reads each field independently, so mapping the same
// canonical source into two output fields is technically harmless — but
// it's almost always an accidental duplicate pick, so we flag it.
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

export default function FieldsBuilder({ fields, onChange }) {
  const sourceCounts = countBySource(fields);

  function updateField(index, patch) {
    const next = fields.map((f, i) => (i === index ? { ...f, ...patch } : f));
    onChange(next);
  }

  function updateType(index, type) {
    const validNormalize = normalizeOptionsFor(type).some(
      (o) => o.value === (fields[index].normalize ?? ""),
    );
    updateField(index, {
      type,
      normalize: validNormalize ? fields[index].normalize : null,
    });
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
        <strong className="text-ink">Source</strong> is <em>not</em> renameable:
        it has to be one of the real canonical fields below, since that's what
        actually gets read. A source that doesn't match anything real is never
        an error by itself — it just resolves to an empty value, handled by the
        "On missing field" setting above.
      </p>

      {fields.length > 0 && (
        <div className="mb-2 hidden grid-cols-[1fr_1fr_100px_110px_70px_36px] gap-2 px-1 text-xs font-semibold uppercase tracking-wide text-ink-soft md:grid">
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
          const normalizeOptions = normalizeOptionsFor(field.type);
          const hasCustomSource =
            field.from &&
            !SOURCE_PATH_OPTIONS.some((o) => o.value === field.from);
          const isDuplicateSource =
            field.from && (sourceCounts.get(field.from) ?? 0) > 1;

          return (
            <div
              key={index}
              className="grid grid-cols-1 gap-2 rounded-lg border border-line-soft bg-white p-2.5 md:grid-cols-[1fr_1fr_100px_110px_70px_36px] md:items-center"
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
                  onChange={(e) => updateField(index, { from: e.target.value })}
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
              <select
                value={field.type}
                onChange={(e) => updateType(index, e.target.value)}
                className={inputClass}
              >
                {TYPE_OPTIONS.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <select
                value={field.normalize ?? ""}
                onChange={(e) =>
                  updateField(index, { normalize: e.target.value || null })
                }
                className={inputClass}
              >
                {normalizeOptions.map((n) => (
                  <option key={n.value} value={n.value}>
                    {n.label}
                  </option>
                ))}
              </select>
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
