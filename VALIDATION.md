# Validation record

Public deployment verified: 2026-11-11T22:43:01.284195+00:00 (UTC).

- Live site: https://juliermorris-max.github.io/tracy-content-opportunities/
- Repository: https://github.com/juliermorris-max/tracy-content-opportunities
- Successful workflow: https://github.com/juliermorris-max/tracy-content-opportunities/actions/runs/43113422836
- GitHub Actions gate, search and Pages deployment jobs all completed successfully.
- All 42 automated tests passed locally and on GitHub’s runner.
- Latest successful search: 2026-11-11T22:38:31.926971+00:00.
- Sources responding: 23/23; current postings reviewed: 1613; verified current matches: 3.
- Report HTML, results.json and jobs.csv all returned HTTP 200 without authentication, and their contents agree.
- Every application link displayed in the public report returned HTTP 200 in a separate post-deployment check.
- Report/history commits, Pages artifact upload and diagnostic artifact upload succeeded.
- Daily workflow is active. Summer/winter cron gates select approximately 08:17 Europe/Madrid; delayed runners and both daylight-saving transition dates are covered by tests.
- No external Python packages, paid API or Selenium cleanup module required.

## Verified current opportunities

- Canonical: Content Marketing Manager — https://job-boards.greenhouse.io/canonical/jobs/8046372
- Canonical: Storytelling and narrative lead — https://job-boards.greenhouse.io/canonical/jobs/8288908
- Canonical: Content marketing lead — https://job-boards.greenhouse.io/canonical/jobs/6943565

All current matches advertise EMEA remote locations. The report labels Spain eligibility for confirmation rather than promising country-level hiring eligibility. None publishes compensation.

## Selection and recovery checks

Tests cover title and description relevance, adjacent roles, seniority, contract preference, explicit currency/period pay comparisons, Spain and Barcelona eligibility, US-only exclusions, employer restrictions overriding feed labels, deduplication, malformed feeds, HTML escaping, direct application-link discovery, closed listings, generic redirects, network failure preservation, prior-match source failure preservation and healthy empty reports.

The paid-access writing listing was excluded during screening. Another freelance listing used a worldwide feed label but its employer application page listed CA/US; it was excluded and the conflict is recorded in diagnostics.

HTML was parsed; template placeholders, unique IDs, local downloads, HTTPS links and absence of private resume details were checked. The resume and contact details were not uploaded. The existing private job-search-agent-system repository was not modified.

## Remaining limits

- Visual desktop/mobile browser QA was unavailable because the cloud browser-control tools were not exposed. No screenshot or browser-layout verification is claimed.
- The morning schedule is enabled and its timing logic is tested, but the next unattended scheduled occurrence has not yet happened. GitHub can delay schedules and disable workflows under its inactivity policies; recovery is documented in README.md.
- Live posting checks verify current accessibility and application evidence, not an employment offer or guaranteed Spain eligibility. Availability and requirements can change.

The first deployment attempt failed while Pages was disabled. After the owner enabled GitHub Actions as the Pages source, rerunning only the failed deployment job succeeded using the completed search artifact.
