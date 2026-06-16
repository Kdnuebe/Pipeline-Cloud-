-- ===========================================================================
-- DATAMART GOLD #1 — Demande & revenus par zone × heure × jour
-- Répond à : "Quelles zones/heures génèrent le plus de courses et de revenu ?"
-- RGPD : HAVING COUNT(*) >= 5  => k-anonymat (pas de maille < 5 courses exposée).
-- ===========================================================================
SELECT
    pu_borough,
    pu_zone,
    pickup_hour,
    pickup_dow_iso,
    COUNT(*)                          AS trips,
    ROUND(SUM(total_amount), 2)       AS revenue_total,
    ROUND(AVG(total_amount), 2)       AS avg_ticket,
    ROUND(AVG(trip_distance), 2)      AS avg_distance_mi,
    ROUND(AVG(trip_duration_min), 1)  AS avg_duration_min
FROM silver_trips
WHERE pu_borough IS NOT NULL
GROUP BY pu_borough, pu_zone, pickup_hour, pickup_dow_iso
HAVING COUNT(*) >= 5
