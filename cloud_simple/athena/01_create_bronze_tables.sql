-- ===========================================================================
-- ÉTAPE 1 — Créer la base et les tables BRONZE dans Athena
-- ---------------------------------------------------------------------------
-- À FAIRE AVANT : avoir uploadé le dossier ./data/bronze vers
--   s3://VOTRE-BUCKET/bronze/   (voir le guide, partie « Uploader vers S3 »)
--
-- COMMENT : dans la console AWS → Athena → Éditeur de requêtes, remplace
-- "VOTRE-BUCKET" par le nom de ton bucket (Édition → Remplacer), puis exécute
-- chaque bloc (bouton « Exécuter »).
-- ===========================================================================

CREATE DATABASE IF NOT EXISTS nyc_taxi;

-- --- Table des courses (lit tous les Parquet sous bronze/trips/) ------------
CREATE EXTERNAL TABLE IF NOT EXISTS nyc_taxi.bronze_trips (
  vendorid              int,
  tpep_pickup_datetime  timestamp,
  tpep_dropoff_datetime timestamp,
  passenger_count       double,
  trip_distance         double,
  ratecodeid            double,
  store_and_fwd_flag    string,
  pulocationid          int,
  dolocationid          int,
  payment_type          bigint,
  fare_amount           double,
  extra                 double,
  mta_tax               double,
  tip_amount            double,
  tolls_amount          double,
  improvement_surcharge double,
  total_amount          double,
  congestion_surcharge  double,
  airport_fee           double,
  driver_email          string,
  driver_pseudo         string
)
STORED AS PARQUET
LOCATION 's3://VOTRE-BUCKET/bronze/trips/';

-- --- Table de référence des zones -------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS nyc_taxi.bronze_zones (
  location_id  bigint,
  borough      string,
  zone_name    string,
  service_zone string
)
STORED AS PARQUET
LOCATION 's3://VOTRE-BUCKET/bronze/zones/';

-- --- Table météo ------------------------------------------------------------
CREATE EXTERNAL TABLE IF NOT EXISTS nyc_taxi.bronze_weather (
  weather_date        string,
  temperature_2m_mean double,
  temperature_2m_max  double,
  precipitation_sum   double
)
STORED AS PARQUET
LOCATION 's3://VOTRE-BUCKET/bronze/weather/';

-- Vérification : doit renvoyer ~3 000 000 pour 1 mois
SELECT COUNT(*) AS nb_courses_bronze FROM nyc_taxi.bronze_trips;
