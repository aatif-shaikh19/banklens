-- BankLens 2.0 — Advanced Analytics Queries
-- These 5 queries demonstrate window functions, CTEs, and anti-joins
-- Run these in BigQuery console or dbt test after marts are built

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 1: Rolling 30-day fraud rate per channel (window function)
-- Skill: SUM() OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
-- ─────────────────────────────────────────────────────────────────────────────

-- [Query 1 SQL will go here in Phase 2]

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 2: RFM Segmentation (Recency, Frequency, Monetary)
-- Skill: NTILE(), CONCAT(), CASE multi-condition
-- ─────────────────────────────────────────────────────────────────────────────

-- [Query 2 SQL will go here in Phase 2]

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 3: Month-over-Month Volume Variance
-- Skill: LAG() window function, percentage change calculation
-- ─────────────────────────────────────────────────────────────────────────────

-- [Query 3 SQL will go here in Phase 2]

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 4: Campaign Response Rate by Risk Band
-- Skill: Multi-table join, conditional aggregation
-- ─────────────────────────────────────────────────────────────────────────────

-- [Query 4 SQL will go here in Phase 2]

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 5: High-Risk Customers Who Received Campaign Offers (THE KILLER QUERY)
-- Skill: Anti-join pattern, business insight surfacing
-- This query IS the business justification for BankLens 2.0
-- ─────────────────────────────────────────────────────────────────────────────

-- [Query 5 SQL will go here in Phase 2]
