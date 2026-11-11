# Tracy's daily job search

A public, mobile-friendly shortlist of writing, content design and strategy roles compatible with living in Barcelona. The site needs no account or installation. This repository contains no resume, email address, citizenship data or uploaded source documents.

## For the owner

Once deployed, send Tracy the GitHub Pages URL. Results refresh after each successful morning search, rather than when she opens the page. The page displays the latest successful search time, source coverage and a warning when that report is over 36 hours old. Filters are optional; application links work without JavaScript.

**Manual refresh:** open the repository on GitHub → **Actions** → **Daily job search** → **Run workflow** → **Run workflow**. No code or terminal work is needed. A failed search does not replace the live report. Failure details are in the run's **search-diagnostics** download.

**Schedule:** about 08:17 Europe/Madrid. Two daily UTC triggers are filtered to one local morning run. The gate uses the intended cron slot, so delayed GitHub runners still execute. Spain's daylight-saving changes are covered by tests. GitHub does not guarantee exact start times.

**Inactivity:** public-repository scheduled workflows can be disabled after 60 days without repository activity. Successful searches commit the new report and history daily, maintaining repository activity. This is a mitigation, not a guarantee against GitHub policy changes, disabled Actions, account restrictions or prolonged failures. If GitHub shows an inactivity notice, open **Actions → Daily job search → Enable workflow**, then **Run workflow**. Enable GitHub Actions failure notifications in GitHub notification settings if you want alerts. These steps are recovery instructions, not routine setup work for Tracy.

## Hosting

**Live public website:** https://juliermorris-max.github.io/tracy-content-opportunities/

Publication succeeded, and anonymous access to the report and downloads was verified. The first GitHub-hosted search passed all 42 tests, reviewed 1,613 postings across 23 sources, and produced 3 checked matches. See `VALIDATION.md` for verification details and limits.

The repository uses GitHub Actions as its Pages publishing source. The **Daily job search** workflow runs tests, performs the search, saves the successful report/history and deploys `docs/`. No resume or personal contact information is published.

No paid services, AI keys, Selenium, ChromeDriver or third-party Python packages are required. Standard free GitHub Pages and public-repository Actions are used, subject to GitHub's current limits.

## Search design

Python 3.11+ and its standard library. `sources.json` holds verified public Greenhouse, Lever and Ashby board endpoints plus Remotive and Arbeitnow public feeds. Employer coverage includes Barcelona employers Typeform, Wallapop, Perk, Lodgify and Docplanner, European/international technology employers, and health/wellbeing companies Flo Health and Modern Health. Source availability changes; failures are visible and never trigger CAPTCHA workarounds.

- Search descriptions for UX writing, strategy, governance, operations, writing, editorial, SEO, localization and accessibility. Adjacent titles require several independent content skills plus explicit content responsibilities.
- Prefer relevant contract / freelance work, then part-time; strong full-time roles remain eligible. Seniority and health/wellbeing experience increase rank. Explicit EUR annual and USD daily/hourly pay is compared with the stated targets when periods are published. Missing salary is allowed; currencies are never converted and ambiguous dollar symbols are not treated as verified USD.
- Require Barcelona as an office location, or remote Spain / Europe / EU / EMEA / worldwide eligibility. Regional matches clearly say to confirm Spain. Citizenship does not override geographic restrictions. Unknown remote geography, US-only roles, internships, junior roles, engineering and unrelated program management are rejected.
- Deduplicate by canonical URL and company/title. First-found dates persist across successful runs. Current output contains current feed matches only; expired jobs are not retained just to inflate results. Published dates older than 120 days are excluded where supplied. Dates are not invented when feeds omit them.
- Validate public posting pages, application evidence, closed-role markers and generic redirects. Aggregator postings must expose a direct public application link, which is checked separately; employer restrictions override feed labels. No applications are submitted.
- Three concurrent feed requests; sequential link checks with 0.4-second pauses; bounded timeouts; one retry for selected transient HTTP errors. Respect `Retry-After` up to 30 seconds; larger delays fail that source. No retries for 401/403, no bypasses or fingerprint evasion.
- Publish only with a majority of configured sources responding and nonzero postings reviewed. Preserve the prior report if a source supplying prior matches fails, or most candidate link checks have transient failures. A healthy search with no relevant matches publishes an honest empty result.
- Search diagnostics are retained even on failure. Results are staged before promotion. GitHub deploys only after tests, search and report/history commit succeed, leaving the prior deployment live if any earlier step fails.

Ranking uses explainable rules, not an AI model. It cannot prove employment eligibility, detect every misleading advertisement, or guarantee all relevant jobs are found. Descriptions, location evidence, pay, requirements and travel expectations should be checked by the applicant. No browser-only job boards are scraped.

## Developer reference

```sh
python -m unittest discover -s tests -v
python job_search_automation.py
```

`docs/` is the generated static site. `data/history.json` stores first-found dates. `data/last_attempt.json` records source/link health. `templates/report.html` defines the report. No package installation is needed.

### Changes from the attached prototype

The CSV/report concepts, company grouping, summary statistics and green visual accents are retained. The original Selenium scraper and largely US/Android-focused URL list were replaced because they extracted title-bearing navigation and unrelated jobs without location evidence. The original profiles were for Julie and Android, not Tracy. Tracy's resume informed the replacement relevance rules; the resume itself is not in this project.

The missing `selenium_cleanup.py` dependency is resolved by removing Selenium and all its imports. The replacement runs on a clean Python 3.12 installation without that file. The old README's suggestions to retry blocking responses with Selenium were not adopted.

### Verification limits

Automated tests and real network searches were executed locally; see `VALIDATION.md`. GitHub-hosted execution, live Pages access and visual browser checks are not yet verified. Browser-control tools were absent in this cloud session; no screenshot or mobile-browser test is claimed.
