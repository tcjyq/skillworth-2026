# SkillWorth Live Design QA

Status: **PASSED**

## Visual target

- Accepted reference: local generated visual reference (not committed)
- Implemented screenshot: `apps/web/.qa/market-1440.png`
- Side-by-side comparison: `apps/web/.qa/reference-comparison.png`
- Native verification viewport: 1440×900; additional checks at 1366×768 and 412×915.
- Screenshot method: Playwright with installed Microsoft Edge channel against the Next.js production server.
- Browser plugin was not available in the active toolset, so the requested Playwright fallback was used.

## Reference comparison

1. App shell: matched the 60px dark top rail, left brand, restrained text navigation, right data/search controls, and amber active state.
2. Color system: matched warm-black background, near-black surfaces, low-contrast separators, off-white text, amber accent, and semantic green/red only.
3. Market layout: retained the accepted first-concept market-map canvas on the left and the third-concept market status/movers/source ledger on the right.
4. Density and shape: preserved terminal density, open canvas, 1px rules, 0–4px radii, and avoided card-grid, neon, gradient, glass, and oversized rounding.
5. Typography: used Geist-style sans and mono number treatment with Chinese UI labels and original technology names.
6. Data integrity: the reference contains illustrative six-month bubbles; the live Demo API has eight jobs, one source, and one observed month. The implementation therefore renders the same map frame with a low-confidence/insufficient-trend state instead of fabricating positions.
7. Responsive behavior: desktop keeps map/right rail; tablet stacks secondary rails; mobile uses a single column and fixed bottom navigation with no horizontal overflow.

## Page QA

- Market Pulse: filters, selected navigation, map labels, low-confidence state, source status and 1440/1366/mobile spacing checked.
- Skill Explorer: searchable rail, asset header, metric strip, trend chart, salary strip and empty related-skill state checked.
- Role Intelligence: role selection, core-skill chart, metric hierarchy and unavailable-dimension states checked.
- Skill Graph: zoom/pan/drag configuration, focus select, hover adjacency, click focus and inspector checked; empty graph is explicit when support edges are absent.
- Portfolio / Optimizer: input states, API submission paths, disabled states, result layouts and estimation disclaimer checked.
- Data Quality / Methodology: chart labels, missing API metrics, source status, formula blocks and long-page spacing checked.
- Command palette: Ctrl+K open, filtering and navigation verified in desktop and mobile Playwright projects.

## Automated evidence

- Lint: passed.
- TypeScript: passed.
- Vitest: 3 files, 6 tests passed.
- Playwright: 18 tests passed across desktop and mobile.
- Production build: passed; all requested routes generated.
- Browser console: no page errors in production screenshot pass.
- Overflow audit: all eight pages passed at 1440 and 1366; Market, Skills, Portfolio and Graph passed at 412 mobile width.

## Intentional deviations

- No synthetic trend bubbles, rising/declining rankings, skill relations, extraction F1, dedup rate, or role distributions were inserted when the FastAPI contract did not provide reliable values.
- Data Quality labels extraction F1 and dedup rate as `API 暂未提供`.
- Role Intelligence labels experience/city/source detail as unavailable instead of substituting proxy metrics.

The implementation is faithful to the accepted visual system and preserves the project's no-hardcoded-analysis rule.
