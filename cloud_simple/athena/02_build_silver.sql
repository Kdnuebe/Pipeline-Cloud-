-- ===========================================================================
-- ÉTAPE 2 — Construire la couche SILVER dans le cloud (Athena fait le travail)
-- ---------------------------------------------------------------------------
-- C'est ICI que le CLOUD transforme les données : nettoyage, jointures (zones +
-- météo), features, et RGPD (on ne garde QUE l'identifiant pseudonymisé).
-- Athena écrit le résultat en Parquet dans s3://VOTRE-BUCKET/silver/trips/ et
-- crée la table nyc_taxi.silver_trips.
--
-- ⚠️ Si tu RELANCES cette requête : supprime d'abord la table et vide le dossier
--    DROP TABLE IF EXISTS nyc_taxi.silver_trips;   (+ vider s3://VOTRE-BUCKET/silver/ dans la console S3)
-- ===========================================================================

CREATE TABLE nyc_taxi.silver_trips
WITH (format = 'PARQUET', external_location = 's3://VOTRE-BUCKET/silver/trips/') AS
SELECT
    t.vendorid                                          AS vendor_id,
    t.tpep_pickup_datetime                              AS pickup_ts,
    t.tpep_dropoff_datetime                             AS dropoff_ts,
    CAST(t.tpep_pickup_datetime AS DATE)                AS pickup_date,
    EXTRACT(HOUR FROM t.tpep_pickup_datetime)           AS pickup_hour,
    EXTRACT(DOW  FROM t.tpep_pickup_datetime)           AS pickup_dow_iso,   -- 1=Lundi .. 7=Dimanche
    CASE WHEN EXTRACT(DOW FROM t.tpep_pickup_datetime) >= 6 THEN TRUE ELSE FALSE END AS is_weekend,
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

    -- RGPD : pseudonyme uniquement (driver_email en clair n'est PAS sélectionné)
    t.driver_pseudo                                     AS driver_pseudo
FROM nyc_taxi.bronze_trips t
LEFT JOIN nyc_taxi.bronze_zones   pz ON t.pulocationid = pz.location_id
LEFT JOIN nyc_taxi.bronze_zones   dz ON t.dolocationid = dz.location_id
LEFT JOIN nyc_taxi.bronze_weather w  ON CAST(t.tpep_pickup_datetime AS DATE) = CAST(w.weather_date AS DATE)
WHERE t.tpep_pickup_datetime IS NOT NULL
  AND t.tpep_dropoff_datetime > t.tpep_pickup_datetime
  AND t.trip_distance > 0 AND t.trip_distance < 200
  AND t.fare_amount >= 0 AND t.total_amount >= 0
  AND t.passenger_count BETWEEN 1 AND 8
  AND date_diff('minute', t.tpep_pickup_datetime, t.tpep_dropoff_datetime) BETWEEN 1 AND 240;

-- Vérification
SELECT COUNT(*) AS nb_lignes_silver FROM nyc_taxi.silver_trips;
