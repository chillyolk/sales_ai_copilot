SELECT
  customer_account_name,
  customer_name,
  customer_level,
  sales_name,
  SUM(cost_amount) AS cost_amount,
  SUM(order_cnt) AS order_cnt,
  SUM(gmv_amount) AS gmv_amount,
  SUM(overdue_receivable_amount) AS overdue_receivable_amount,
  MAX(available_balance_amount) AS available_balance_amount
FROM ads_auto_commercial_daily_wide
WHERE stat_date BETWEEN :start_date AND :end_date
  AND (:sales_name IS NULL OR sales_name = :sales_name)
  AND (:department_name IS NULL OR sales_department_name = :department_name)
GROUP BY customer_account_name, customer_name, customer_level, sales_name
HAVING overdue_receivable_amount > 0 OR order_cnt = 0 OR available_balance_amount <= 1000
ORDER BY overdue_receivable_amount DESC, cost_amount DESC
LIMIT :top_n
