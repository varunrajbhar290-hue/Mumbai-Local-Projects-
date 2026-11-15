# Power BI dashboard build guide

All visuals must display **SIMULATED — estimated crowding patterns**. This package contains a build guide and DAX, not a tested PBIX report.

## Layout (16:9 canvas)
- Header: project title plus prominent simulation disclaimer.
- Left rail: line, station, day_type, direction and train_type slicers.
- Top: average Crowding Index; busiest hour; least crowded line cards.
- Middle left: hour × line heatmap. Middle right: hourly mean load chart split by direction.
- Bottom: departure detail table with departure_time, station, train_type, estimated load, index, category; optionally add date/time slicers.

## Build steps
1. Get Data → Text/CSV → simulated_clean.csv → Transform Data. Rename table `Departures`.
2. Set departure_time to Date/Time, service_date to Date, hour to Whole Number, loads/gaps/index to Decimal Number, and flags to True/False. Check locale when parsing dates. Load.
3. Create the following measures with New measure. All KPIs respect active slicers. Aggregates are station-departure-weighted, not passenger-weighted.
4. Add three card visuals and the measures below. Busiest hour means highest mean estimated load; ties resolve to earliest hour. Least crowded line uses average index; ties resolve alphabetically.
5. Add a Matrix with line in Rows, hour in Columns, and Average Crowding Index in Values. Apply background conditional formatting using a fixed 0–100 scale (green, amber, red); disable totals if they confuse interpretation.
6. Add a line chart: hour on X (ascending, categorical), Average Estimated Load on Y, direction in Legend. The hour axis combines the two simulated service dates unless filtered.
7. Add the slicers and detail table described above; enable interactions so they filter all visuals. Format loads as decimals with a custom suffix `"% capacity"`, NOT Percentage format (values are 0–145, not 0–1).
8. Add a tooltip explaining the index formula and station-departure unit. Check the unfiltered cards: 43.95, 18:00, Harbour.
9. Validate selected line/day filters against pandas grouped outputs. Save the report locally. Do not label it live or predictive.

```dax
Average Estimated Load = AVERAGE(Departures[estimated_passenger_load])

Average Crowding Index = AVERAGE(Departures[crowding_index])

Station Departures = COUNTROWS(Departures)

Busiest Hour =
VAR Candidates =
    ADDCOLUMNS(
        VALUES(Departures[hour]),
        "MeanLoad", CALCULATE([Average Estimated Load])
    )
VAR Winner = TOPN(1, Candidates, [MeanLoad], DESC, Departures[hour], ASC)
RETURN IF(COUNTROWS(Candidates)=0, BLANK(),
    FORMAT(MAXX(Winner, Departures[hour]), "00") & ":00")

Least Crowded Line =
VAR Candidates =
    ADDCOLUMNS(
        VALUES(Departures[line]),
        "MeanIndex", CALCULATE([Average Crowding Index])
    )
VAR Winner = TOPN(1, Candidates, [MeanIndex], ASC, Departures[line], ASC)
RETURN CONCATENATEX(Winner, Departures[line], ", ")
```

These instructions and expressions are supplied for manual validation in Power BI Desktop; they were not executed in this environment.
