SELECT
  SUM(cost_amount) AS cost_amount,
  SUM(recharge_amount) AS recharge_amount,
  SUM(confirmed_revenue_amount) AS confirmed_revenue_amount,
  SUM(received_amount) AS received_amount,
  SUM(contract_amount) AS contract_amount,
  SUM(valid_lead_cnt) AS valid_lead_cnt,
  SUM(order_cnt) AS order_cnt,
  SUM(gmv_amount) AS gmv_amount,
  SUM(overdue_receivable_amount) AS overdue_receivable_amount,
  SUM(impression_cnt) AS impression_cnt,
  SUM(click_cnt) AS click_cnt
FROM ads_auto_commercial_daily_wide
WHERE stat_date BETWEEN :start_date AND :end_date
  AND (:sales_name IS NULL OR sales_name = :sales_name)
  AND (:department_name IS NULL OR sales_department_name = :department_name)
