"""
pipeline.py
BookWorld data pipeline: extracts, transforms, and loads sales data from multiple sources
(CSV, SQLite, web scraping, exchange rate API) into a final aggregated dataset (sales by country).
"""

import pandas as pd
import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Display options: show all columns and avoid line wrapping in the terminal
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)

# Path to the SQLite reference database (already populated with business reference tables:
# category_rules, channels, countries
DB_NAME = "data/bookworld_reference.db"

# Path to the website to scrap (first page only, as required by the exam)
BOOKSTOSCRAP_URL = "https://books.toscrape.com/"


def extract():
    """
    Extract raw data from the CSV file, the SQLite reference database,
    and the book catalog (1st page of books.toscrape.com).
    """

    # Sales data (CSV) Read "sales_raw.csv" file store it as df_sales_raw
    try:
        df_sales_raw = pd.read_csv("data/sales_raw.csv", encoding="utf-8")
        ## print(df_sales_raw.shape)
        ## print(df_sales_raw.head())
    except FileNotFoundError:
        print("Error: data/sales_raw.csv not found")
        raise
    except Exception as e:
        print(f"Unexpected error while reading the CSV file: {e}")
        raise

    # Bookworld reference data (SQLite) Open a connexion to the reference database
    try:
        conn = sqlite3.connect(DB_NAME)
    except sqlite3.Error as e:
        print(f"Error: could not connect to the reference database ({DB_NAME}): {e}")
        raise

    # category_rules: margin rate, strategic flag and sales status per book category
    try:
        query_category_rules = "SELECT * FROM category_rules"
        df_category_rules = pd.read_sql_query(query_category_rules, conn)
    except Exception as e:
        print(f"Error while reading table 'category_rules': {e}")
        conn.close()
        raise

    # channels: acquisition cost, grouping and active status per sales channel
    try:
        query_channels = "SELECT * FROM channels"
        df_channels = pd.read_sql_query(query_channels, conn)
    except Exception as e:
        print(f"Error while reading table 'channels': {e}")
        conn.close()
        raise

    # countries: currency, VAT rate and active status per country
    try:
        query_countries = "SELECT * FROM countries"
        df_countries = pd.read_sql_query(query_countries, conn)
    except Exception as e:
        print(f"Error while reading table 'countries': {e}")
        conn.close()
        raise

    # Close the connection once all reference tables have been read
    conn.close()

    # Books to Scrape catalog (Web scrapping, 1st page only)
    try:
        response = requests.get(BOOKSTOSCRAP_URL)
        # Force UTF-8 decoding : requests sometimes guesses the wrong encoding from the response headers,
        # which corrupts special characters like "£"
        response.encoding = "utf-8"
    except requests.exceptions.RequestException as e:
        print(f"Error: could not reach the catalog page ({BOOKSTOSCRAP_URL}): {e}")
        raise

    soup = BeautifulSoup(response.text, "html.parser")

    # Each book on the 1st page is wrapped in <article class = "product_pod">
    books = []
    for product in soup.find_all("article", class_="product_pod"):
        # Reset at the start of each iteration - to avoid conflict with except block
        title = None

        try:
            # Title is store in the "title" attribute of the <a> tag inside <h3>
            title = product.h3.a["title"]

            # href is a relative link (e.g. "catalogue/a-light-in-the-attic_1000/index.html") 
            # urljoin combines it with the base URL to get an absolute URL
            relative_url = product.h3.a["href"]
            book_url = urljoin(BOOKSTOSCRAP_URL, relative_url)

            # Explore book's detail page to retreive data
            detail_response = requests.get(book_url)
            detail_response.encoding = "utf-8"
            detail_soup = BeautifulSoup(detail_response.text, "html.parser")

            # Scope 1: <div class="col-sm-6 product_main"> holds:
            # price, stock, status and star rating for THE CURRENT book.
            product_main = detail_soup.find("div", class_="col-sm-6 product_main")

            # Price is the text content of <p class="price_color">, e.g. "£47.82"
            price_text = product_main.find("p", class_="price_color").text
            price_gbp = float(price_text.replace("£", ""))

            # Availability text, e.g. "In stock (22 available)"
            availability = product_main.find("p", class_="instock availability").text.strip()

            # Star rating is encoded as a CSS class on <p class="star-rating Three">
            # (word form: One, Two, Three, Four, Five), not as visible text
            rating_words = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
            rating_tag = product_main.find("p", class_="star-rating")
            rating = rating_words[rating_tag["class"][1]]

            # Scope 2: <table class="table table-striped"> holds:
            # UPC, prices, tax and review count.
            # Row order on this site is always:
            # UPC, Product Type, Price (excl. tax), Price (incl. tax), Tax, Availability, Number of reviews
            table = detail_soup.find("table", class_="table table-striped")
            rows = table.find_all("tr")
            upc = rows[0].find("td").text.strip()
            price_excl_tax = rows[2].find("td").text.strip()
            price_incl_tax = rows[3].find("td").text.strip()
            tax = rows[4].find("td").text.strip()
            number_of_reviews = rows[6].find("td").text.strip()

            # Category comes from the breadcrumb, outside product_main:
            # "Home > Books > Category > Book title" -> the 3rd <a> (index 2)
            breadcrumb = detail_soup.find("ul", class_="breadcrumb")
            category = breadcrumb.find_all("a")[2].text.strip()

            books.append({
                "book_name": title,
                "price_gbp": price_gbp,
                "book_url": book_url,
                "category": category,
                "upc": upc,
                "price_excl_tax": price_excl_tax,
                "price_incl_tax": price_incl_tax,
                "tax": tax,
                "number_of_reviews": number_of_reviews,
                "availability": availability,
                "rating": rating,
            })
        except Exception as e:
            # title may still be None if the failure happened before it was read
            book_label = title if title is not None else "unknown book"
            print(f"Warning: could not scrape book '{book_label}', skipping it: {e}")
            continue


    df_catalog = pd.DataFrame(books)

    # Exchange rate (Frankfurter API)
    # v2/rate/{base}/{quote} returns a flat response for a single currency pair
    last_exchange_rates_url = "https://api.frankfurter.dev/v2/rate/GBP/EUR"

    try:
        response_rate = requests.get(last_exchange_rates_url)
        data_rate = response_rate.json()
        gbp_to_eur = data_rate["rate"]
    except requests.exceptions.RequestException as e:
        # The exchange rate service is unreachable (network, issue, timeout...)
        print(f"Error: could not reach the exchange rate API ({last_exchange_rates_url}): {e}")
        raise
    except (ValueError, KeyError) as e:
        # Valid requests.get() but response not JSON or
        # did not contain the expected "rate" key (unexepected API response shape)
        print(f"Error: unexpected exchange rate API response: {e}")
        raise
    # For consistency, single-row API response convert in a DataFrame
    df_exchange_rate = pd.DataFrame([data_rate])

    data = {
        "sales_raw": df_sales_raw,
        "category_rules": df_category_rules,
        "channels": df_channels,
        "countries": df_countries,
        "book_catalog": df_catalog,
        "exchange_rate": df_exchange_rate,
    }
    return data

def transform(data):
    """
    Clean, enrich and aggregate the raw data extracted by extract() into
    the final sales_by_country dataset.
    """

    df_sales_raw = data["sales_raw"]
    df_category_rules = data["category_rules"]
    df_channels = data["channels"]
    df_countries = data["countries"]
    df_catalog =  data["book_catalog"]
    df_exchange_rate = data["exchange_rate"]



if __name__ == "__main__":
    extract()

