# 汽车商业化广告 AI 自助分析 Demo Mock 数据生成计划

## Context
用户需要一份用于 AI 自助分析 Demo 的 mock 数据，业务场景是汽车垂媒/汽车商业化广告产品售卖，类似汽车之家、懂车帝等平台的商业化经营分析。数据需要覆盖客户充值、广告消耗、已充值待消耗、收入、销售组织、汽车品牌、城市、广告产品、线索转化等核心场景，并体现行业内常见的数据分布和业务逻辑。

## 目标输出
- **文件格式**：CSV
- **数据行数**：30000 行
- **建议输出路径**：`/Users/bytedance/ads_auto_commercial_mock_20260101_20260531.csv`
- **时间范围**：2026-01-01 至 2026-05-31
- **数据粒度**：`日期 × 客户资金账户 × 客户/门店 × 品牌/车系 × 广告产品 × 城市 × 销售`

## 字段范围
基于上一版宽表方案生成完整分析宽表，包含：

### 维度字段
- 日期：`stat_date`、`stat_month`
- 地域：`province_name`、`city_name`、`city_tier`、`region_name`
- 业务：`business_line`、`industry_name`、`sub_industry_name`
- 客户账户：`customer_account_id`、`customer_account_name`、`customer_id`、`customer_name`
- 客户层级：`customer_type`、`customer_level`
- 经销商：`dealer_group_id`、`dealer_group_name`、`dealer_store_id`、`dealer_store_name`
- 汽车：`brand_id`、`brand_name`、`brand_country_type`、`vehicle_series_id`、`vehicle_series_name`、`vehicle_energy_type`、`vehicle_price_range`
- 广告产品：`ad_product_id`、`ad_product_name`、`ad_product_type`
- 渠道代理：`sales_channel`、`agent_id`、`agent_name`
- 销售组织：`sales_id`、`sales_name`、`sales_department_name`、`sales_role`

### 指标字段
- 资金：`recharge_amount`、`cash_recharge_amount`、`grant_recharge_amount`、`refund_amount`、`net_recharge_amount`
- 消耗与余额：`cost_amount`、`cash_cost_amount`、`grant_cost_amount`、`pending_cost_amount`、`opening_balance_amount`、`closing_balance_amount`、`frozen_amount`、`available_balance_amount`
- 财务收入：`confirmed_revenue_amount`、`unconfirmed_revenue_amount`、`invoice_amount`
- 合同回款：`contract_amount`、`new_contract_amount`、`renewal_contract_amount`、`receivable_amount`、`received_amount`、`overdue_receivable_amount`
- 广告效果：`impression_cnt`、`click_cnt`、`valid_click_cnt`、`ctr`、`cpc`、`cpm`
- 线索转化：`lead_cnt`、`valid_lead_cnt`、`phone_lead_cnt`、`form_lead_cnt`、`im_lead_cnt`、`test_drive_lead_cnt`、`lead_conversion_rate`、`cost_per_lead`
- 汽车销售转化：`arrival_cnt`、`test_drive_cnt`、`order_cnt`、`vehicle_sales_cnt`、`gmv_amount`、`cost_per_order`、`roi`
- 活跃：`active_campaign_cnt`、`active_customer_cnt`

## 组织与销售人员生成规则
- 部门覆盖以下 4 个：
  - 经销商业务中心
  - 大客户业务中心
  - 车品业务中心
  - 商业伙伴发展业务中心
- 销售人员总数严格为 **432 人**。
- 销售角色包含：
  - `Leader`
  - `一线销售`
- 人员在部门间不均匀分布，建议大致分布：
  - 经销商业务中心：约 190 人，覆盖最多本地经销商客户
  - 大客户业务中心：约 95 人，服务主机厂、KA、大型经销商集团
  - 车品业务中心：约 80 人，服务车品、后市场、金融保险等客户
  - 商业伙伴发展业务中心：约 67 人，服务代理商、渠道商、服务商
- 每个部门设置少量 Leader，其余为一线销售。Leader 可承担更高金额、更大客户的业绩归因。

## 行业合理性生成规则

### 品牌与车系
覆盖市面常见汽车品牌，包含但不限于：
- 自主/新能源：比亚迪、吉利、长安、长城、奇瑞、广汽埃安、蔚来、小鹏、理想、零跑、问界、极氪、深蓝、腾势、红旗
- 合资：大众、丰田、本田、日产、别克、现代、起亚、福特、雪佛兰、马自达
- 豪华：宝马、奔驰、奥迪、雷克萨斯、沃尔沃、凯迪拉克、保时捷、路虎、捷豹、林肯
- 进口/新能源代表：特斯拉、MINI、smart 等

品牌国别/类型需要与品牌匹配：自主、合资、豪华、进口、新势力等。能源类型与品牌和车系大致匹配，新能源品牌纯电/增程/插混占比更高，传统合资燃油占比更高。

### 城市与地域
覆盖全国热门汽车消费城市，包含一线、新一线、二线和部分三四线高潜城市，例如：北京、上海、广州、深圳、杭州、成都、重庆、武汉、南京、苏州、天津、西安、郑州、长沙、青岛、宁波、佛山、东莞、合肥、济南、厦门、无锡、福州、昆明、沈阳、长春、哈尔滨、石家庄、南昌、南宁、太原、贵阳、乌鲁木齐、兰州等。

城市需映射到省份、城市线级和大区。

### 广告产品
覆盖汽车垂媒常见商业化产品：
- 信息流广告：效果广告，曝光和点击规模大，CPC/CPM 中等
- 搜索广告：效果广告，点击意图强，CPC 较高，转化率较高
- 品牌专区：品牌广告，合同金额和曝光高，线索转化相对低
- 线索通：线索广告，线索量和有效线索率较高
- 开屏广告：品牌广告，曝光极高，CPM 较高，线索转化弱
- 车型页资源位：品牌/效果结合，适合车系分析
- 内容营销：种草类产品，曝光和互动中等
- 经销商会员/店铺推广：面向本地经销商，金额中小但客户数多

### 客户与渠道
- 客户类型覆盖：主机厂、经销商集团、4S 店、单店经销商、代理商、二手车商、车品/后市场客户。
- 客户等级覆盖：KA、区域大客户、普通 SMB、长尾客户。
- 售卖渠道覆盖：直销、代理、服务商、渠道商、自助开户。
- 大客户业务中心更偏 KA、主机厂、集团客户；经销商业务中心更偏 4S 店和本地经销商；商业伙伴发展业务中心更偏代理、服务商、渠道商。

## 指标逻辑与合理性规则
- 金额不得为负，余额不得为负。
- `net_recharge_amount = recharge_amount - refund_amount`。
- `cost_amount = cash_cost_amount + grant_cost_amount`。
- `closing_balance_amount ≈ opening_balance_amount + recharge_amount - refund_amount - cost_amount`。
- `available_balance_amount = closing_balance_amount - frozen_amount`，且不小于 0。
- `ctr = click_cnt / impression_cnt`。
- `cpc = cost_amount / click_cnt`。
- `cpm = cost_amount / impression_cnt * 1000`。
- `lead_conversion_rate = valid_lead_cnt / valid_click_cnt`。
- `cost_per_lead = cost_amount / valid_lead_cnt`。
- `cost_per_order = cost_amount / order_cnt`。
- `roi = gmv_amount / cost_amount`。
- `lead_cnt >= valid_lead_cnt`。
- `valid_lead_cnt >= arrival_cnt >= test_drive_cnt >= order_cnt >= vehicle_sales_cnt`。
- 品牌广告类产品曝光高、CTR 较低、直接线索转化较低。
- 搜索广告和线索通 CPC/CPL 较高，但线索转化更好。
- 经销商客户单笔金额更分散，大客户/主机厂金额更集中。
- 一线和新一线城市消耗、合同和 GMV 更高，但 CPC/CPL 也更高。
- 新能源和新势力品牌在线索、试驾、订单转化上略高于传统燃油品牌。

## 实施步骤
1. 使用 Python 生成 432 名销售人员主数据，确保部门、角色不均匀分布。
2. 构造品牌、车系、城市、省份、大区、广告产品、客户类型、渠道等基础枚举。
3. 按 2026-01-01 至 2026-05-31 日期范围生成 30000 行事实数据。
4. 根据部门、客户类型、广告产品、城市线级、品牌类型生成差异化金额、曝光、点击、线索、订单和 GMV。
5. 按业务公式回填 CTR、CPC、CPM、CPL、ROI、余额、收入、回款等派生指标。
6. 输出 CSV 文件到 `/Users/bytedance/ads_auto_commercial_mock_20260101_20260531.csv`。
7. 抽样检查字段完整性、行数、日期范围、432 名销售人员、4 个部门覆盖、金额和转化链路合理性。

## 验证方式
- 检查 CSV 行数是否为 30000。
- 检查 `stat_date` 最小值为 2026-01-01，最大值为 2026-05-31。
- 检查 `sales_id` 去重数量是否为 432。
- 检查 4 个部门均有数据，且销售人员不均匀分布。
- 检查金额、余额、CTR、CPC、CPM、CPL、ROI 等派生指标与公式一致或在合理误差内。
- 检查汽车品牌、城市、广告产品、客户类型覆盖完整。
- 抽样查看高消耗客户、低消耗客户、品牌广告、效果广告、线索广告的数据表现是否符合行业常识。
