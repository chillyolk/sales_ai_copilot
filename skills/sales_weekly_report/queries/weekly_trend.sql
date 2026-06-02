SELECT
  stat_month,
  MIN(stat_date) AS start_date,
  MAX(stat_date) AS end_date,
  SUM(cost_amount) AS cost_amount,
  SUM(valid_lead_cnt) AS valid_lead_cnt,
  SUM(order_cnt) AS order_cnt,
  SUM(gmv_amount) AS gmv_amount
FROM ads_auto_commercial_daily_wide
WHERE stat_date BETWEEN :trend_start_date AND :end_date
  AND (:sales_name IS NULL OR sales_name = :sales_name)
  AND (:department_name IS NULL OR sales_department_name = :department_name)
GROUP BY stat_month
ORDER BY stat_month
