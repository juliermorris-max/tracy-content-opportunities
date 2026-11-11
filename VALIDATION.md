# Validation record

Latest successful real search: 2026-11-11T22:25:06.891964+00:00 (UTC).

- Sources responding: 23/23
- Current postings reviewed: 1613
- Relevant candidates: 4
- Direct job/application pages validated: 3
- Automated unit/integration tests: 42 passed on Python 3.12.
- HTML parsed; template placeholders resolved; unique IDs, HTTPS links, local CSV/JSON downloads and absence of private resume details checked.
- Daily workflow configured for 08:17 Europe/Madrid with summer/winter UTC gating. Winter, summer, both DST transition dates, delayed runners and manual runs tested.
- Failure tests confirm the previous report survives network failure and failure of a source that supplied previous matches.
- No external Python packages or Selenium cleanup module required.

## Verified current roles

- Canonical: Content Marketing Manager — https://job-boards.greenhouse.io/canonical/jobs/8046372
- Canonical: Storytelling and narrative lead — https://job-boards.greenhouse.io/canonical/jobs/8288908
- Canonical: Content marketing lead — https://job-boards.greenhouse.io/canonical/jobs/6943565

All current matches are EMEA remote listings. Spain eligibility is regional rather than a confirmed country-level hiring promise and is labelled for confirmation. No current match publishes compensation.

## Excluded after validation

- Remotive: Link validation: Link validation: Employer location conflicts with Spain eligibility from feed (https://remotive.com/remote-jobs/writing/freelance-copywriter-1749306)

The excluded freelance listing used a worldwide feed label but its application page stated CA/US. Its feed salary also differed from its per-word application-page rates; it is not published. The paid-access writing listing was rejected by relevance screening.

## Not yet verified

- GitHub connection verified for juliermorris-max. Repository creation was rejected by both GraphQL and REST with “Resource not accessible by integration”; installed permissions include contents/actions/workflows write but omit administration/Pages. Account owner must create a new public repository and select GitHub Actions as its Pages source. No existing repository was modified. Hosted workflow execution and Pages publication remain unverified.
- Anonymous public-site access: no deployment yet.
- Visual desktop/mobile browser QA: cloud browser-control tools unavailable. Following the Sites skill, no improvised preview server or alternate browser-control path was used.
- A future scheduled run: schedule logic tested, but no hosted automation has run.

No deployed URL, screenshot or end-to-end hosting success is claimed.

## GitHub-hosted verification

- Public repository: https://github.com/juliermorris-max/tracy-content-opportunities
- Hosted workflow run: https://github.com/juliermorris-max/tracy-content-opportunities/actions/runs/43113422836
- All 42 tests passed on GitHub's runner.
- All 23 sources responded; 1,613 postings reviewed; 3 verified matches published into the repository report at 2026-11-11T22:38:31.926971+00:00.
- First-found history and latest report were successfully committed by the workflow.
- Pages artifact and diagnostics artifact uploaded successfully.
- The daily workflow is active with its two gated UTC schedules.
- Deployment job failed with HTTP 404 because GitHub Pages has not yet been enabled. Anonymous public URL also returns 404. Account owner must select GitHub Actions as the Pages source. Afterward, rerun only the failed deployment job; the completed search artifact can be reused.
- No change was made to the existing private job-search-agent-system repository.
