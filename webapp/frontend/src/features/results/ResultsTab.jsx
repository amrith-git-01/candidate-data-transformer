import { useState } from "react";
import Card from "../../components/Card";
import Pagination from "../../components/Pagination";
import Spinner from "../../components/Spinner";
import { Badge, ConfidenceBadge } from "../../components/Badge";
import { useResultsQuery } from "../../api/queries";

const PAGE_SIZE = 8;

const CELL = "px-4 py-3 align-top whitespace-normal break-words";

function CellText({ children, muted = false }) {
  if (
    children === null ||
    children === undefined ||
    children === "" ||
    children === "—"
  ) {
    return <span className="text-ink-soft/50">—</span>;
  }
  return <div className={muted ? "text-ink-soft" : "text-ink"}>{children}</div>;
}

function CellList({ items, muted = true }) {
  if (!items?.length) return <span className="text-ink-soft/50">—</span>;
  return (
    <div className="space-y-1">
      {items.map((item, i) => (
        <div key={i} className={muted ? "text-ink-soft" : "text-ink"}>
          {item}
        </div>
      ))}
    </div>
  );
}

function formatLocation(profile) {
  if (profile.location) {
    const { city, region, country } = profile.location;
    return [city, region, country].filter(Boolean).join(", ") || null;
  }
  return (
    [profile.city, profile.region, profile.country]
      .filter(Boolean)
      .join(", ") || null
  );
}

function profileName(profile) {
  return profile.full_name ?? profile.name ?? null;
}

function profileEmails(profile) {
  if (profile.emails?.length) return profile.emails;
  return profile.primary_email ? [profile.primary_email] : [];
}

function profilePhones(profile) {
  if (profile.phones?.length) return profile.phones;
  return profile.phone ? [profile.phone] : [];
}

function profileSkills(profile) {
  if (profile.skill_names?.length) return profile.skill_names;
  if (!profile.skills?.length) return [];
  return profile.skills.map((s) => (typeof s === "string" ? s : s.name));
}

function profileExperience(profile) {
  if (profile.experience?.length) {
    return profile.experience.map((entry) => {
      const role = [entry.title, entry.company].filter(Boolean).join(" @ ");
      const dates = [entry.start, entry.end].filter(Boolean).join(" – ");
      const parts = [role, dates, entry.summary].filter(Boolean);
      return parts.join(" · ");
    });
  }
  const titles = profile.job_titles ?? [];
  const companies = profile.companies ?? [];
  const count = Math.max(titles.length, companies.length);
  if (!count) return [];
  return Array.from({ length: count }, (_, i) => {
    const title = titles[i];
    const company = companies[i];
    if (title && company) return `${title} @ ${company}`;
    return title || company;
  }).filter(Boolean);
}

function profileEducation(profile) {
  if (profile.education?.length) {
    return profile.education.map((entry) => {
      const degree = [entry.degree, entry.field].filter(Boolean).join(" ");
      const year = entry.end_year ? ` (${entry.end_year})` : "";
      if (degree) return `${degree} @ ${entry.institution}${year}`;
      return `${entry.institution}${year}`;
    });
  }
  const schools = profile.schools ?? [];
  const degrees = profile.degrees ?? [];
  const fields = profile.fields_of_study ?? [];
  const count = Math.max(schools.length, degrees.length, fields.length);
  if (!count) return [];
  return Array.from({ length: count }, (_, i) => {
    const degree = [degrees[i], fields[i]].filter(Boolean).join(" ");
    const school = schools[i];
    if (degree && school) return `${degree} @ ${school}`;
    return degree || school;
  }).filter(Boolean);
}

function profileId(profile) {
  return profile.candidate_id ?? profile.id ?? null;
}

function profileLinkFields(profile) {
  if (profile.links) {
    return {
      linkedin: profile.links.linkedin ?? null,
      github: profile.links.github ?? null,
      other: [profile.links.portfolio, ...(profile.links.other ?? [])].filter(
        Boolean,
      ),
    };
  }
  return {
    linkedin: profile.linkedin ?? null,
    github: profile.github ?? null,
    other: [],
  };
}

function LinkCell({ url }) {
  if (!url) return <span className="text-ink-soft/50">—</span>;
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      className="break-all text-brand-700 hover:text-brand-800 hover:underline"
    >
      {url.replace(/^https?:\/\//, "")}
    </a>
  );
}

function OtherLinksCell({ urls }) {
  if (!urls?.length) return <span className="text-ink-soft/50">—</span>;
  return (
    <div className="space-y-1">
      {urls.map((url) => (
        <LinkCell key={url} url={url} />
      ))}
    </div>
  );
}

const COLUMNS = [
  { key: "id", label: "ID", minWidth: "min-w-[120px]" },
  { key: "name", label: "Name", minWidth: "min-w-[140px]" },
  { key: "contact", label: "Contact", minWidth: "min-w-[180px]" },
  { key: "location", label: "Location", minWidth: "min-w-[140px]" },
  { key: "headline", label: "Headline", minWidth: "min-w-[200px]" },
  { key: "years", label: "Years", minWidth: "min-w-[56px]" },
  { key: "skills", label: "Skills", minWidth: "min-w-[160px]" },
  { key: "experience", label: "Experience", minWidth: "min-w-[200px]" },
  { key: "education", label: "Education", minWidth: "min-w-[180px]" },
  { key: "linkedin", label: "LinkedIn", minWidth: "min-w-[140px]" },
  { key: "github", label: "GitHub", minWidth: "min-w-[140px]" },
  { key: "other_links", label: "Other links", minWidth: "min-w-[140px]" },
  { key: "matched_by", label: "Matched by", minWidth: "min-w-[96px]" },
  { key: "confidence", label: "Confidence", minWidth: "min-w-[88px]" },
];

export default function ResultsTab() {
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, error } = useResultsQuery(page, PAGE_SIZE);
  const profiles = data?.profiles ?? [];

  return (
    <Card
      title="Canonical profiles"
      description="Full profile details from the latest pipeline run, sorted by name."
    >
      {isError && <p className="mb-3 text-sm text-rose-600">{error.message}</p>}
      {isLoading ? (
        <Spinner label="Loading results…" />
      ) : profiles.length === 0 ? (
        <div className="py-16 text-center text-sm text-ink-soft">
          No results yet — run the pipeline from the Run tab.
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-line-soft">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-line-soft">
                  {COLUMNS.map((col) => (
                    <th
                      key={col.key}
                      className={`${CELL} text-left text-xs font-semibold uppercase tracking-wide text-ink-soft ${col.minWidth}`}
                    >
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {profiles.map((profile) => {
                  const emails = profileEmails(profile);
                  const phones = profilePhones(profile);
                  const { linkedin, github, other } =
                    profileLinkFields(profile);
                  const id = profileId(profile);

                  return (
                    <tr
                      key={id ?? profileName(profile)}
                      className="border-b border-line-soft last:border-b-0 hover:bg-canvas"
                    >
                      <td className={CELL}>
                        {id ? (
                          <div className="font-mono text-xs text-ink-soft break-all">
                            {id}
                          </div>
                        ) : (
                          <span className="text-ink-soft/50">—</span>
                        )}
                      </td>
                      <td className={`${CELL} font-medium`}>
                        <CellText>{profileName(profile)}</CellText>
                      </td>
                      <td className={CELL}>
                        <CellList items={emails} />
                        {phones.length > 0 && (
                          <div className="mt-2 space-y-1">
                            {phones.map((phone) => (
                              <div key={phone} className="text-ink-soft">
                                {phone}
                              </div>
                            ))}
                          </div>
                        )}
                        {emails.length === 0 && phones.length === 0 && (
                          <span className="text-ink-soft/50">—</span>
                        )}
                      </td>
                      <td className={CELL}>
                        <CellText muted>{formatLocation(profile)}</CellText>
                      </td>
                      <td className={CELL}>
                        <CellText muted>{profile.headline}</CellText>
                      </td>
                      <td className={CELL}>
                        <CellText>{profile.years_experience ?? null}</CellText>
                      </td>
                      <td className={CELL}>
                        <CellText muted>
                          {profileSkills(profile).join(", ") || null}
                        </CellText>
                      </td>
                      <td className={CELL}>
                        <CellList items={profileExperience(profile)} />
                      </td>
                      <td className={CELL}>
                        <CellList items={profileEducation(profile)} />
                      </td>
                      <td className={CELL}>
                        <LinkCell url={linkedin} />
                      </td>
                      <td className={CELL}>
                        <LinkCell url={github} />
                      </td>
                      <td className={CELL}>
                        <OtherLinksCell urls={other} />
                      </td>
                      <td className={CELL}>
                        {profile.matched_by ? (
                          <Badge tone="brand">{profile.matched_by}</Badge>
                        ) : (
                          <span className="text-ink-soft/50">—</span>
                        )}
                      </td>
                      <td className={CELL}>
                        <ConfidenceBadge value={profile.overall_confidence} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={data.total}
            onPageChange={setPage}
          />
        </>
      )}
    </Card>
  );
}
