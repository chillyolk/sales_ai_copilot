SELECT
  customer_account_name,
  customer_name,
  customer_level,
  sales_name,
  SUM(cost_amount) AS cost_amount,
  SUM(valid_lead_cnt) AS valid_lead_cnt,
  SUM(order_cnt) AS order_cnt,
  SUM(gmv_amount) AS gmv_amount,
  MAX(available_balance_amount) AS available_balance_amount,
  SUM(overdue_receivable_amount) AS overdue_receivable_amount
FROM ads_auto_commercial_daily_wide
WHERE stat_date BETWEEN :start_date AND :end_date
  AND (:sales_name IS NULL OR sales_name = :sales_name)
  AND (:department_name IS NULL OR sales_department_name = :department_name)
GROUP BY customer_account_name, customer_name, customer_level, sales_name
HAVING cost_amount > 0 AND gmv_amount > 0 AND overdue_receivable_amount = 0
ORDER BY (gmv_amount / NULLIF(cost_amount, 0)) DESC, valid_lead_cnt DESC
LIMIT :top_n
