import { useEffect, useState } from "react";
import { ChevronDown, PlayCircle, AlertTriangle } from "lucide-react";
import Card from "../../components/Card";
import ConfigSelector from "../../components/ConfigSelector";
import SegmentedControl from "../../components/SegmentedControl";
import Toggle from "../../components/Toggle";
import Spinner from "../../components/Spinner";
import FieldsBuilder, { hasDuplicateSources } from "./FieldsBuilder";
import {
  useConfigQuery,
  useConfigsQuery,
  useRunPipelineMutation,
} from "../../api/queries";

const DEFAULT_CONFIG = {
  use_canonical_schema: true,
  fields: [],
  include_confidence: true,
  include_provenance: true,
  on_missing: "null",
};

// Mirrors ProjectionConfig's own field defaults (src/models.py), used when
// merging a fetched preset that omits a key — NOT the same as DEFAULT_CONFIG,
// which is just this form's initial state before anything has loaded.
const MODEL_DEFAULTS = {
  use_canonical_schema: false,
  fields: [],
  include_confidence: true,
  include_provenance: true,
  on_missing: "null",
};

const SCHEMA_MODE_OPTIONS = [
  { value: true, label: "Canonical schema" },
  { value: false, label: "Custom fields" },
];

const ON_MISSING_OPTIONS = [
  { value: "null", label: "Null" },
  { value: "omit", label: "Omit" },
  { value: "error", label: "Error" },
];

const ON_MISSING_HELP = {
  null: "Missing fields are kept in the output with a null value.",
  omit: "Missing fields are dropped from the output entirely.",
  error: "The whole profile is rejected if a required field is missing.",
};

export default function RunPipelineTab() {
  const [selectedConfig, setSelectedConfig] = useState("default");
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [enrichGithub, setEnrichGithub] = useState(false);
  const [showJson, setShowJson] = useState(false);

  const { data: configNames = [] } = useConfigsQuery();
  const { data: fetchedConfig } = useConfigQuery(selectedConfig);
  const runMutation = useRunPipelineMutation();

  useEffect(() => {
    if (fetchedConfig) {
      setConfig({ ...MODEL_DEFAULTS, ...fetchedConfig });
    }
  }, [fetchedConfig]);

  function patchConfig(patch) {
    setConfig((prev) => ({ ...prev, ...patch }));
  }

  function handleRun() {
    runMutation.mutate({ config, enrichGithub });
  }

  const hasFieldErrors =
    !config.use_canonical_schema && hasDuplicateSources(config.fields);

  const canonicalFieldNames = [
    "candidate_id",
    "full_name",
    "emails",
    "phones",
    "location",
    "links",
    "headline",
    "years_experience",
    "skills",
    "experience",
    "education",
  ];

  return (
    <div className="space-y-6">
      <Card
        title="Projection config"
        description="Shape the output schema interactively — no JSON editing required."
        actions={
          configNames.length > 0 && (
            <ConfigSelector
              options={configNames}
              value={selectedConfig}
              onChange={setSelectedConfig}
            />
          )
        }
      >
        <div className="space-y-5">
          <div>
            <p className="mb-2 text-sm font-medium text-ink">Schema mode</p>
            <SegmentedControl
              options={SCHEMA_MODE_OPTIONS}
              value={config.use_canonical_schema}
              onChange={(value) => patchConfig({ use_canonical_schema: value })}
            />
          </div>

          {config.use_canonical_schema ? (
            <div className="rounded-lg border border-line-soft bg-canvas p-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">
                Fields included in the full canonical schema
              </p>
              <div className="flex flex-wrap gap-1.5">
                {canonicalFieldNames.map((name) => (
                  <span
                    key={name}
                    className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-ink-soft"
                  >
                    {name}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <p className="mb-2 text-sm font-medium text-ink">Custom fields</p>
              <FieldsBuilder
                fields={config.fields}
                onChange={(fields) => patchConfig({ fields })}
              />
            </div>
          )}

          <div className="grid gap-4 border-t border-line-soft pt-5 sm:grid-cols-2">
            <Toggle
              checked={config.include_confidence}
              onChange={(checked) =>
                patchConfig({ include_confidence: checked })
              }
              label="Include confidence scores"
              description="Adds overall_confidence to every profile."
            />
            <Toggle
              checked={config.include_provenance}
              onChange={(checked) =>
                patchConfig({ include_provenance: checked })
              }
              label="Include provenance trail"
              description="Adds a per-field source + method breakdown."
            />
          </div>

          <div className="border-t border-line-soft pt-5">
            <p className="mb-2 text-sm font-medium text-ink">
              On missing field
            </p>
            <SegmentedControl
              options={ON_MISSING_OPTIONS}
              value={config.on_missing}
              onChange={(value) => patchConfig({ on_missing: value })}
              size="sm"
            />
            <p className="mt-2 text-xs text-ink-soft">
              {ON_MISSING_HELP[config.on_missing]}
            </p>
          </div>

          <div className="border-t border-line-soft pt-4">
            <button
              type="button"
              onClick={() => setShowJson((v) => !v)}
              className="inline-flex items-center gap-1 text-xs font-medium text-ink-soft hover:text-ink"
            >
              <ChevronDown
                size={14}
                className={
                  showJson
                    ? "rotate-180 transition-transform"
                    : "transition-transform"
                }
              />
              {showJson ? "Hide" : "Preview"} JSON payload
            </button>
            {showJson && (
              <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-canvas p-3 text-xs text-ink-soft">
                {JSON.stringify(config, null, 2)}
              </pre>
            )}
          </div>
        </div>
      </Card>

      <Card
        title="Run"
        description="Parses recruiter CSV + ATS JSON + notes, matches identities, merges, projects, and validates."
      >
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-ink-soft">
            <input
              type="checkbox"
              checked={enrichGithub}
              onChange={(e) => setEnrichGithub(e.target.checked)}
              className="h-4 w-4 rounded border-line-soft text-brand-600 focus:ring-brand-200"
            />
            Enrich with GitHub (requires network / token, slower)
          </label>
          <button
            onClick={handleRun}
            disabled={runMutation.isPending || hasFieldErrors}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-700 disabled:opacity-50"
          >
            <PlayCircle size={16} />
            {runMutation.isPending ? "Running…" : "Run pipeline"}
          </button>
          {runMutation.isPending && (
            <Spinner label="Matching, merging, projecting…" />
          )}
        </div>

        {hasFieldErrors && (
          <p className="mt-3 flex items-center gap-1.5 text-sm text-rose-600">
            <AlertTriangle size={14} className="shrink-0" />
            Fix the duplicate source(s) in the custom fields above before
            running.
          </p>
        )}

        {runMutation.isError && (
          <p className="mt-3 text-sm text-rose-600">
            {runMutation.error.message}
          </p>
        )}

        {runMutation.isSuccess && (
          <p className="mt-3 text-sm text-emerald-700">
            Produced <strong>{runMutation.data.profile_count}</strong> canonical
            profiles. Switch to the Results tab to view them.
          </p>
        )}
      </Card>
    </div>
  );
}
