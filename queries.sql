-- MySQL 8+. SIMULATED data only. Load simulated_clean.csv with your import wizard.
-- Import booleans as 0/1, departure_time as DATETIME, numeric columns as DECIMAL.
-- Each row is one train stopping at one station, not one unique train or passenger.
CREATE TABLE IF NOT EXISTS departures (
 service_id VARCHAR(150), line VARCHAR(20), station VARCHAR(40),
 direction VARCHAR(30), departure_time DATETIME, train_type VARCHAR(10),
 day_type VARCHAR(10), estimated_passenger_load DECIMAL(7,2),
 load_imputed BOOLEAN, hour TINYINT, time_band VARCHAR(20), is_peak BOOLEAN,
 service_date DATE, gap_minutes DECIMAL(7,2), gap_imputed BOOLEAN,
 crowding_index DECIMAL(6,2), crowding_category VARCHAR(12),
 PRIMARY KEY(service_id,station)
);
-- 1. Compare mean simulated load by line.
SELECT line, ROUND(AVG(estimated_passenger_load),2) AS mean_load
FROM departures GROUP BY line ORDER BY mean_load DESC;

-- 2. Compare clock-based peak and non-peak periods within each day type.
SELECT day_type, is_peak, COUNT(*) AS station_departures,
 ROUND(AVG(estimated_passenger_load),2) AS mean_load
FROM departures GROUP BY day_type,is_peak ORDER BY day_type,is_peak;

-- 3. Rank station averages within each line (RANK preserves boundary ties).
WITH station_means AS (
 SELECT line,station,AVG(estimated_passenger_load) AS mean_load
 FROM departures GROUP BY line,station
), ranked AS (
 SELECT *,RANK() OVER(PARTITION BY line ORDER BY mean_load DESC) AS station_rank
 FROM station_means
)
SELECT * FROM ranked WHERE station_rank<=5 ORDER BY line,station_rank;
-- This sample contains only 3 stations per line, so returns at most 3, not 5.

-- 4. Describe hourly estimated load trends, separated by day type.
SELECT line,day_type,HOUR(departure_time) AS departure_hour,
 ROUND(AVG(estimated_passenger_load),2) AS mean_load
FROM departures GROUP BY line,day_type,HOUR(departure_time)
ORDER BY line,day_type,departure_hour;

-- 5. Select the lowest-index departure for every station, direction and date.
WITH choices AS (
 SELECT *,ROW_NUMBER() OVER (
 PARTITION BY line,station,direction,service_date
 ORDER BY crowding_index,estimated_passenger_load,departure_time,service_id) AS rn
 FROM departures
)
SELECT line,station,direction,departure_time,crowding_index
FROM choices WHERE rn=1 ORDER BY line,station,direction,departure_time;

-- 6. Return up to 3 lowest-index departures within an inclusive ±30-minute window.
SET @station='Andheri'; SET @line='Western';
SET @direction='towards_terminus'; SET @preferred='2026-11-09 09:00:00';
SELECT line,station,direction,departure_time,train_type,
 estimated_passenger_load,gap_minutes,crowding_index
FROM departures
WHERE station=@station AND line=@line AND direction=@direction
 AND departure_time BETWEEN DATE_SUB(@preferred,INTERVAL 30 MINUTE)
 AND DATE_ADD(@preferred,INTERVAL 30 MINUTE)
ORDER BY crowding_index,estimated_passenger_load,
 ABS(TIMESTAMPDIFF(SECOND,@preferred,departure_time)),departure_time,service_id
LIMIT 3;
