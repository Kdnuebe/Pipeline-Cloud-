-- ===========================================================================
-- COUCHE SILVER — Nettoyage, typage, jointures, features, RGPD
-- ---------------------------------------------------------------------------
-- SQL PORTABLE : tourne tel quel dans DuckDB (local) et dans Athena/Trino (AWS).
-- Le seul élément spécifique au moteur est le jeton __DOW__ (jour de semaine ISO),
-- remplacé par le runner (voir transformations/run_local.py et le job Glue cloud).
--
-- Tables sources attendues (créées par le runner) :
--   bronze_trips, bronze_zones, bronze_weather
-- Sortie : SELECT consommé par "CREATE TABLE silver_trips AS (...)".
-- ===========================================================================
SELECT
    t.vendorid                                          AS vendor_id,
    t.tpep_pickup_datetime                              AS pickup_ts,
    t.tpep_dropoff_datetime                             AS dropoff_ts,
    CAST(t.tpep_pickup_datetime AS DATE)                AS pickup_date,
    CAST(EXTRACT(HOUR FROM t.tpep_pickup_datetime) AS INTEGER) AS pickup_hour,
    __DOW__                                             AS pickup_dow_iso,   -- 1=Lundi .. 7=Dimanche
    CASE WHEN __DOW__ >= 6 THEN TRUE ELSE FALSE END     AS is_weekend,
    CASE WHEN EXTRACT(HOUR FROM t.tpep_pickup_datetime) BETWEEN 7 AND 9
           OR EXTRACT(HOUR FROM t.tpep_pickup_datetime) BETWEEN 16 AND 19
         THEN TRUE ELSE FALSE END                       AS is_rush_hour,

    CAST(t.passenger_count AS INTEGER)                  AS passenger_count,
    t.trip_distance,
    date_diff('minute', t.tpep_pickup_datetime, t.tpep_dropoff_datetime) AS trip_duration_min,

    t.pulocationid                                      AS pu_location_id,
    t.dolocationid                                      AS do_location_id,
    pz.borough                                          AS pu_borough,
    pz.zone_name                                        AS pu_zone,
    dz.borough                                          AS do_borough,
    dz.zone_name                                        AS do_zone,

    CAST(t.payment_type AS INTEGER)                     AS payment_type,
    t.fare_amount,
    t.tip_amount,
    t.total_amount,
    CASE WHEN t.fare_amount > 0
         THEN ROUND(100.0 * t.tip_amount / t.fare_amount, 2) END AS tip_pct,

    w.temperature_2m_mean                               AS temp_mean_c,
    w.temperature_2m_max                                AS temp_max_c,
    w.precipitation_sum                                 AS precip_mm,

    -- RGPD : on ne propage QUE l'identifiant pseudonymisé. driver_email (clair)
    -- présent en bronze n'est volontairement PAS sélectionné ici.
    t.driver_pseudo                                     AS driver_pseudo

FROM bronze_trips t
LEFT JOIN bronze_zones   pz ON t.pulocationid = pz.location_id
LEFT JOIN bronze_zones   dz ON t.dolocationid = dz.location_id
LEFT JOIN bronze_weather w  ON CAST(t.tpep_pickup_datetime AS DATE) = CAST(w.weather_date AS DATE)

-- Règles de qualité (valeurs aberrantes filtrées, documentées dans le rapport)
WHERE t.tpep_pickup_datetime IS NOT NULL
  AND t.tpep_dropoff_datetime > t.tpep_pickup_datetime
  AND t.trip_distance > 0 AND t.trip_distance < 200
  AND t.fare_amount >= 0 AND t.total_amount >= 0
  AND t.passenger_count BETWEEN 1 AND 8
  AND date_diff('minute', t.tpep_pickup_datetime, t.tpep_dropoff_datetime) BETWEEN 1 AND 240
