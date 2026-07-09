-- schema_final.sql
-- BookWorld project - Final database schema
--
-- RGPD note: the "sales" table intentionally does NOT include
-- customer_first_name / customer_last_name. These columns exist in the raw
-- CSV source (sales_raw.csv) but are not needed for the final use of this
-- database (sales aggregation by country), so they are excluded at the
-- schema level rather than filtered out after the fact. See the final
-- report for the full justification.

CREATE TABLE IF NOT EXISTS countries (
    country_code   TEXT PRIMARY KEY,
    country_name   TEXT NOT NULL,
    currency_code  TEXT,
    vat_rate       REAL,
    region         TEXT,
    is_active      INTEGER
);

CREATE TABLE IF NOT EXISTS channels (
    channel_code           TEXT PRIMARY KEY,
    channel_name           TEXT NOT NULL,
    acquisition_cost_gbp   REAL,
    channel_group          TEXT,
    is_active              INTEGER
);

CREATE TABLE IF NOT EXISTS category_rules (
    category_name           TEXT PRIMARY KEY,
    margin_rate              REAL,
    strategic_flag            INTEGER,
    default_channel_code     TEXT,
    is_active                 INTEGER,
    FOREIGN KEY (default_channel_code) REFERENCES channels (channel_code)
);

-- No FOREIGN KEY on "category": books.toscrape.com has many more real
-- categories (e.g. "Poetry", "Fiction", "History") than the 10 defined in
-- category_rules, which only covers a curated subset for this exercise.
-- A strict FK would reject most scraped books. Same limitation as
-- country_code in "sales" below.
CREATE TABLE IF NOT EXISTS book_catalog (
    book_name           TEXT PRIMARY KEY,
    price_gbp            REAL,
    book_url              TEXT,
    category               TEXT,
    upc                     TEXT,
    price_excl_tax          REAL,
    price_incl_tax           REAL,
    tax                       REAL,
    number_of_reviews         INTEGER,
    availability                TEXT,
    rating                       INTEGER
);

-- No customer_first_name / customer_last_name columns (RGPD, see note above).
-- No FOREIGN KEY on country_code -> countries.country_code: some sales
-- reference a country code absent from the reference table (e.g. "NL",
-- present in sales but with no corresponding row in countries). A strict
-- FK would reject those inserts. This limitation is documented in the
-- final report rather than silently worked around.
CREATE TABLE IF NOT EXISTS sales (
    order_id        TEXT PRIMARY KEY,
    order_date      TEXT,
    book_name       TEXT,
    country_code    TEXT,
    channel_code    TEXT,
    quantity        INTEGER,
    discount_rate   REAL,
    revenue_gbp     REAL,
    FOREIGN KEY (book_name) REFERENCES book_catalog (book_name),
    FOREIGN KEY (channel_code) REFERENCES channels (channel_code)
);

CREATE TABLE IF NOT EXISTS exchange_rate (
    date    TEXT PRIMARY KEY,
    base    TEXT,
    quote   TEXT,
    rate    REAL
);

-- country_code is NOT declared as a FOREIGN KEY here either, for the same
-- reason as in "sales" above (the "NL" case has no matching countries row).
CREATE TABLE IF NOT EXISTS sales_by_country (
    country_code        TEXT PRIMARY KEY,
    country_name         TEXT,
    total_orders          INTEGER,
    total_quantity         INTEGER,
    total_revenue_gbp       REAL,
    total_revenue_eur       REAL
);
