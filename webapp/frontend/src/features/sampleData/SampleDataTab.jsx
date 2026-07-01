import { useState } from "react";
import {
  Users,
  FileSpreadsheet,
  Briefcase,
  StickyNote,
  Dices,
} from "lucide-react";
import Card from "../../components/Card";
import Table from "../../components/Table";
import Tabs from "../../components/Tabs";
import Pagination from "../../components/Pagination";
import Spinner from "../../components/Spinner";
import StatChip from "../../components/StatChip";
import { Badge } from "../../components/Badge";
import {
  useGenerateSampleMutation,
  useSourcePageQuery,
} from "../../api/queries";

const SOURCE_TABS = [
  { id: "csv", label: "Recruiter CSV" },
  { id: "ats", label: "ATS JSON" },
  { id: "notes", label: "Recruiter Notes" },
];

const CSV_COLUMNS = [
  { key: "name", label: "Name" },
  { key: "email", label: "Email" },
  { key: "phone", label: "Phone" },
  { key: "current_company", label: "Company" },
  { key: "title", label: "Title" },
  { key: "city", label: "City" },
  { key: "country", label: "Country" },
];

const ATS_COLUMNS = [
  { key: "candidate_name", label: "Name" },
  { key: "contact_email", label: "Email" },
  { key: "contact_phone", label: "Phone" },
  { key: "employer", label: "Company" },
  { key: "job_title", label: "Title" },
  {
    key: "location",
    label: "Location",
    render: (row) =>
      row.location
        ? [row.location.city, row.location.country].filter(Boolean).join(", ")
        : "—",
  },
];

const NOTES_COLUMNS = [
  { key: "candidate", label: "Candidate" },
  {
    key: "notes",
    label: "Notes",
    scroll: true,
    render: (row) => row.notes ?? "—",
  },
];

const COLUMN_MAP = { csv: CSV_COLUMNS, ats: ATS_COLUMNS, notes: NOTES_COLUMNS };
const PAGE_SIZE = 10;

function randomSeed() {
  return Math.floor(Math.random() * 1_000_000);
}

export default function SampleDataTab() {
  const [count, setCount] = useState(500);
  const [seed, setSeed] = useState(randomSeed);
  const [activeSource, setActiveSource] = useState("csv");
  const [page, setPage] = useState(1);

  const generateMutation = useGenerateSampleMutation();
  const { data, isLoading: loadingRows } = useSourcePageQuery(
    activeSource,
    page,
    PAGE_SIZE,
  );

  function handleGenerate() {
    generateMutation.mutate(
      { count: Number(count), seed: Number(seed) },
      { onSuccess: () => setPage(1) },
    );
  }

  function handleSourceChange(source) {
    setActiveSource(source);
    setPage(1);
  }

  const manifest = generateMutation.data;

  return (
    <div className="space-y-6">
      <Card
        title="Generate sample data"
        description="Creates a fresh recruiter CSV, ATS export, and recruiter notes file — the same three sources the pipeline reads."
      >
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col text-sm text-ink-soft">
            Candidate count
            <input
              type="number"
              min={1}
              max={5000}
              value={count}
              onChange={(e) => setCount(e.target.value)}
              className="mt-1.5 w-32 rounded-lg border border-line-soft bg-canvas px-3 py-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand-200"
            />
          </label>
          <label className="flex flex-col text-sm text-ink-soft">
            Seed
            <div className="mt-1.5 flex items-center gap-1.5">
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(e.target.value)}
                className="w-28 rounded-lg border border-line-soft bg-canvas px-3 py-2 text-ink focus:outline-none focus:ring-2 focus:ring-brand-200"
              />
              <button
                type="button"
                onClick={() => setSeed(randomSeed())}
                title="Randomize seed"
                aria-label="Randomize seed"
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-line-soft text-ink-soft transition-colors hover:bg-line-soft hover:text-ink"
              >
                <Dices size={16} />
              </button>
            </div>
          </label>
          <button
            onClick={handleGenerate}
            disabled={generateMutation.isPending}
            className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-700 disabled:opacity-50"
          >
            {generateMutation.isPending ? "Generating…" : "Generate"}
          </button>
          {generateMutation.isPending && (
            <Spinner label="Building personas, writing CSV/JSON/TXT…" />
          )}
        </div>

        <p className="mt-2 text-xs text-ink-soft">
          Generation is deterministic — the same count + seed always reproduces
          the exact same dataset (useful for demos). Roll{" "}
          <Dices size={12} className="inline -translate-y-px" /> for a fresh
          one.
        </p>

        {generateMutation.isError && (
          <p className="mt-3 text-sm text-rose-600">
            {generateMutation.error.message}
          </p>
        )}

        {manifest && (
          <div className="mt-5 border-t border-line-soft pt-5">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatChip
                icon={Users}
                label="Generated"
                value={`${manifest.count} personas`}
              />
              <StatChip
                icon={FileSpreadsheet}
                label="CSV rows"
                value={manifest.source_counts.csv_rows}
              />
              <StatChip
                icon={Briefcase}
                label="ATS candidates"
                value={manifest.source_counts.ats_candidates}
              />
              <StatChip
                icon={StickyNote}
                label="Notes sections"
                value={manifest.source_counts.notes_sections}
              />
            </div>
            <div className="mt-3 flex items-center gap-2 text-sm text-ink-soft">
              GitHub handles:
              <Badge tone="green">{manifest.github_stats.real} real</Badge>
              <Badge tone="red">{manifest.github_stats.fake} fake</Badge>
            </div>
            <p className="mt-3 text-xs text-ink-soft">
              Row counts are lower than the persona count on purpose — each
              candidate is randomly present in only some of the three sources (a
              few are CSV-only, ATS+notes-only, etc.), which is exactly the
              messy multi-source data this pipeline is built to reconcile.
            </p>
          </div>
        )}
      </Card>

      <Card
        title="Preview generated sources"
        actions={
          <Tabs
            tabs={SOURCE_TABS}
            active={activeSource}
            onChange={handleSourceChange}
          />
        }
      >
        {loadingRows ? (
          <Spinner label="Loading rows…" />
        ) : (
          <>
            <Table
              columns={COLUMN_MAP[activeSource]}
              rows={data?.rows}
              emptyMessage="No sample data yet — generate some above."
            />
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={data?.total ?? 0}
              onPageChange={setPage}
            />
          </>
        )}
      </Card>
    </div>
  );
}
