-- ===========================================================================
-- DATAMART GOLD #2 — Analyse des pourboires
-- Répond à : "Quels facteurs (zone, paiement, heure de pointe, météo) influencent
--             le taux de pourboire (tip_pct) ?"
-- RGPD : HAVING COUNT(*) >= 5 => k-anonymat.
-- ===========================================================================
SELECT
    pu_borough,
    payment_type,
    is_rush_hour,
    CASE WHEN precip_mm > 0 THEN TRUE ELSE FALSE END AS is_rainy,
    COUNT(*)                     AS trips,
    ROUND(AVG(tip_pct), 2)       AS avg_tip_pct,
    ROUND(AVG(tip_amount), 2)    AS avg_tip_amount,
    ROUND(AVG(total_amount), 2)  AS avg_ticket
FROM silver_trips
WHERE tip_pct IS NOT NULL
  AND pu_borough IS NOT NULL
GROUP BY pu_borough, payment_type, is_rush_hour,
         CASE WHEN precip_mm > 0 THEN TRUE ELSE FALSE END
HAVING COUNT(*) >= 5
