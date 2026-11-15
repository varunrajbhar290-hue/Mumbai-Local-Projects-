# Mumbai Local Train Crowding Analyzer
**Python · pandas · SQL (MySQL 8+) · Excel · Power BI**

> SIMULATED DATA ONLY. All results are estimated crowding patterns, not verified passenger counts, actual schedules or real-world travel advice.

## Problem statement
Demonstrate how a data analyst can compare directional time-of-day demand, summarize station-departure observations, and rank alternative departure windows. Timetables alone cannot establish passenger occupancy.

## Dataset and assumptions
- 5,365 raw rows → 5,340 cleaned station-departure observations; seed 42.
- Invented service dates: Monday, November 9, 2026 and Saturday, November 14, 2026; these are scenario dates, not observations.
- Western: Borivali, Andheri, Dadar; Central: Thane, Ghatkopar, Dadar; Harbour: Vashi, Chembur, Wadala Road. These are a small illustrative subset, not full line coverage.
- `towards_terminus`: Churchgate for Western and CSMT (formerly CST) for Central/Harbour; reverse is `away_from_terminus`.
- Toy service grid: slow every 10 minutes; fast every 20 minutes on Western/Central; Harbour slow only. Station offsets 9/6 minutes. This is not a reconstruction of real services, stop patterns, running times or frequencies.
- One row = one train stop at one station. A train appears at multiple stops; rows are correlated. Means weight station departures equally, not passengers or unique trains.
- Load is expressed in percentage points of an assumed capacity. 100 means nominal capacity; >100 allows overcapacity. No capacity denominator is measured, and no absolute passenger counts can be recovered.
- Demand uses smooth synthetic peaks centered at 09:18 and 18:48, stronger inbound in the morning and outbound in the evening; weekday/weekend, line, train-type and random effects are explicitly imposed. These are modeling assumptions, not independently discovered behavior.

### Columns
Required: line, station, direction, departure_time, train_type, day_type, estimated_passenger_load.
Extra: service_id (train run), load_imputed, hour, time_band, is_peak, service_date, gap_minutes, gap_imputed, crowding_index, crowding_category.

## Reproduce
```bash
pip install -r requirements.txt
python analysis.py
```
Open `analysis.ipynb` for source, saved execution outputs and charts. The script regenerates the CSVs, chart PNGs, Excel workbook and aggregate outputs. Notebook exports reflect the supplied run.

## 1–2. Setup and cleaning
Raw data intentionally contains 25 duplicate records, 30 missing loads, 30 whitespace/case station inconsistencies and 30 uppercase train-type labels. CSV timestamp strings become datetime; loads become numeric. Remove exact duplicates, canonicalize station names, lowercase train types, and impute missing loads with the median for the same line/station/direction/day type/train type/hour. Mark imputed rows. Assertions test missingness, load range and stop uniqueness.

Time bands: early morning 00:00–07:59 (generated data begins 05:00), morning peak 08:00–10:59, midday 11:00–16:59, evening peak 17:00–20:59, night 21:00–23:59. `is_peak` is clock-based, including weekends and both directions; it is not evidence that every such departure is crowded.

## 3. Exploratory analysis
See outputs/average_by_*.csv and charts/overview.png for means by hour, line, day type and train type. Highest and lowest 10 segments are in outputs/top10_highest.csv and outputs/top10_lowest.csv, with line, station, direction, day type, hour and train type preserved to avoid mixing distinct travel contexts. Every segment contains multiple departures. charts/station_segments.png plots both lists; charts/heatmap.png summarizes hourly index by line.

## 4. Crowding Index
```
load_score = min(100, max(0, estimated_load / 120 * 100))
gap_score  = min(100, max(0, previous_gap_minutes / 20 * 100))
index      = 0.80 * load_score + 0.20 * gap_score
```
Interview explanation: “I normalize estimated occupancy and waiting gaps onto the same 0–100 scale, then give occupancy 80% of the weight and the service gap 20%. Higher means a less desirable departure under these assumptions.”

Index categories: Low [0,25], Moderate (25,50], High (50,75], Very High (75,100]. These cutoffs, 120%-capacity saturation, 20-minute gap saturation and weights are hand-selected and uncalibrated, not industry standards. Loads above 120% saturate the index's load component.

Gaps are computed between consecutive scheduled departures within date/line/station/direction/train type, not across dates or opposite directions. The first gap in each group uses that group's median gap (60 imputed gaps). Fast and slow frequencies are deliberately separate, so this models waiting for the same train type rather than any usable train; overlapping slow/fast alternatives would change the result. Gaps are regular by design and add little temporal variation within a service type. Avoid claims of independent frequency-driven crowding validation or double counting occupancy and waiting.

## 5. Departure-window function
```python
best_departures('Andheri', 'towards_terminus', '2026-11-09 09:00', line='Western')
```
Returns up to three lowest-index scheduled departures within inclusive ±30 minutes, ordered by index, estimated load, closeness to preference, time and service ID. Full date required. No matches returns an empty table. Optional line disambiguates Dadar; omitting it deliberately considers both lines there. There is no destination/stop compatibility check, realtime information or delay forecast.

Example output (all slow, Western, towards terminus):
| Departure | Estimated load (% capacity) | Index | Category |
|---|---:|---:|---|
| 08:59 | 88.65 | 69.10 | High |
| 08:49 | 91.27 | 70.85 | High |
| 08:39 | 95.38 | 73.59 | High |

Least crowded among eligible alternatives does not necessarily mean low crowding. At deployment, only future departures relative to an actual current timestamp should be offered; this is retrospective simulation lookup.

## 6. SQL
queries.sql includes table DDL and six queries: line means, peak vs non-peak, top-five station ranks per line, hourly trends, lowest-index departures using a CTE, and ±30-minute recommendations. The request lists five query topics but asks for six; the sixth implements the recommendation search. The sample has three stations per line, so the top-five query can return only three. RANK retains ties and can return more than five on larger tied datasets. MySQL 8+ required for CTEs/window functions. SQL is authored, not executed against a MySQL server here. Convert CSV True/False strings to 1/0 in the import wizard before loading BOOLEAN fields; column order matches the cleaned CSV.

## 7. Excel and Power BI
crowding_analysis.xlsx contains the clean data, grouped summaries, a native Excel hourly chart, highest/lowest segments, example departures and KPI sheet. POWER_BI.md provides the complete report layout, DAX measures and manual build/validation steps. No PBIX file is included and no Power BI execution is claimed.

## 8. Findings: estimated crowding patterns
1. Central has the highest mean estimated load (52.68%), followed by Western (48.09%) and Harbour (37.41%); imposed line effects and differing service mix partly explain this ranking.
2. Weekday mean load is 51.02% vs 43.28% on weekends, a 7.74-percentage-point difference imposed by the simulation's weekday multiplier.
3. Peak clock bands average 60.15% versus 39.26% outside those bands: a 20.89-point difference. 18:00–18:59 is the highest-load hour overall.
4. Morning inbound mean load is 73.03%, while evening outbound mean load is 74.31%, reproducing the directional assumptions built into the generator.
5. Fast services average 53.81% compared with 44.91% for slow services; this is not a causal fast-train effect because Harbour has no fast-service records and a lower baseline. Overall mean index is 43.95; Harbour has the lowest line mean index (34.94).

### Three commuter-oriented recommendations (illustrative, simulation only)
- Explore off-peak alternatives when flexible, but compare the same line, direction and day type rather than assuming every off-peak train is empty.
- Rank nearby departures inside a personal time window; the Andheri 09:00 example still returns High-category choices, so state absolute crowding as well as relative rank.
- Check train stopping pattern, destination, actual timetable and live conditions before travel; this prototype cannot support real-world departure decisions.

## Limitations and next steps
Only two invented dates, nine line-station pairs (eight distinct station names), fixed headways, no holidays, disruptions, events, weather, destinations or passenger observations. Station effects are simplified and train capacity varies in reality. No inference, statistical significance, forecast accuracy, calibrated occupancy, measured commute benefit, or historical trend claims are supported. Validate against ethically collected occupancy/boarding data and real timetable snapshots before practical use. Test index weights and cutoffs, distinguish joint-service frequency from type-specific frequency, add multiple dates and evaluate on a held-out observed dataset. The generated findings mainly confirm generator assumptions.

## 9. Resume bullets (use only after reproducing and understanding the work)
- Built a reproducible Python/pandas pipeline for 5,340 simulated Mumbai suburban station-departure observations across 3 lines, removing 25 duplicates and flagging/imputing 30 missing load values.
- Designed a transparent 0–100 Crowding Index combining estimated occupancy and service gaps, and implemented a function ranking up to 3 departures within a ±30-minute preference window.
- Produced 6 MySQL 8 analytical queries, an Excel analysis workbook and a Power BI dashboard specification; quantified a simulated 20.89-percentage-point peak/off-peak estimated-load difference.

### Five interview questions and short answers
1. **Can timetables tell you actual crowding?** No. They describe supply, not occupancy. I used explicitly simulated loads and made no observed passenger-count claims.
2. **Why use an 80/20 index?** Occupancy is the primary signal and gaps are a secondary waiting-time proxy. Weights and thresholds are illustrative and require sensitivity checks and real-data validation.
3. **How did you clean missing or inconsistent records?** Removed 25 exact duplicates, standardized 30 station labels and 30 train-type labels, converted types and median-imputed 30 same-segment hourly loads with an audit flag.
4. **What is the analysis grain?** A train stop at a station. The same service appears multiple times, so rows are correlated; mean load is station-departure-weighted, not unique-train or passenger-weighted.
5. **How would you productionize it?** Acquire validated timetable and occupancy feeds, implement data-quality and destination-compatibility checks, calibrate the index, validate on held-out observed dates and monitor drift and delays.
