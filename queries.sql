-- queries.sql
-- BookWorld project - SQL queries used to extract data from bookworld_reference.db
--
-- These queries mirror what is used in pipeline.py (extract()). They are
-- kept here as the final, readable version of the SQL logic used in the
-- project, as required by the exam guidelines (point 1.2).


-- 1. Simple extraction queries (used as-is in extract())

-- Full category_rules table: margin rate, strategic flag and default
-- sales channel per book category
SELECT *
FROM category_rules;

-- Full channels table: acquisition cost and grouping per sales channel
SELECT *
FROM channels;

-- Full countries table: currency, VAT rate and active status per country
SELECT *
FROM countries;


-- 2. Query with a filter
-- Only the active book categories (is_active = 1).
-- One category (Horror) is currently marked inactive in the reference
-- data, similar to the Portugal/Canada situation found in "countries".
SELECT *
FROM category_rules
WHERE is_active = 1;



-- 3. Enrichment query (join), useful for the pipeline
-- Joins category_rules with its default sales channel (channels), to know
-- the acquisition cost and grouping of the channel each category is
-- normally sold through. Column names are explicitly aliased to avoid
-- ambiguity between the two "is_active" columns (one per table).
SELECT
    cr.category_name,
    cr.default_channel_code,
    cr.is_active AS is_active_cat_rules,
    cr.margin_rate,
    cr.strategic_flag,
    c.acquisition_cost_gbp,
    c.channel_code,
    c.channel_group,
    c.channel_name,
    c.is_active AS is_active_channels
FROM category_rules cr
JOIN channels c
    ON c.channel_code = cr.default_channel_code;
