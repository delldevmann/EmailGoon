import subprocess
import streamlit as st
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import pandas as pd
from urllib.parse import urlparse
import logging
import sqlite3
import enum
from tenacity import retry, stop_after_attempt, wait_exponential
from apscheduler.schedulers.background import BackgroundScheduler
from io import BytesIO
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import os

# Configure logging
logging.basicConfig(filename='scraper.log', level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Streamlit page configuration
st.set_page_config(page_title='Enhanced Email Harvester', page_icon='🌾', layout="wide")
st.title("🌾 Streamlit Cloud Email Harvester")

# Ensure Playwright browsers are installed
def install_playwright_browsers():
    try:
        # Check if Playwright's Chromium browser is installed
        if not os.path.exists("/home/appuser/.cache/ms-playwright/chromium-1071/chrome-linux/chrome"):
            st.write("Installing Playwright browsers, please wait...")
            subprocess.run(["playwright", "install"], check=True)
            st.write("Playwright browsers installed successfully.")
        else:
            st.write("Playwright browsers are already installed.")
    except Exception as e:
        st.error(f"Error installing Playwright browsers: {e}")

# Call the function to ensure browsers are installed
install_playwright_browsers()

# Initialize scheduler
scheduler = BackgroundScheduler()

# Proxy Anonymity Level Enum
class AnonymityLevel(enum.IntEnum):
    TRANSPARENT = 1
    ANONYMOUS = 2
    ELITE = 3

# Proxy Scanner Class
class ProxyScanner:
    def __init__(self):
        try:
            # Use a known writable directory for SQLite DB
            self.db_conn = sqlite3.connect('proxy_database.db', check_same_thread=False)
            self.initialize_db()
            self.blacklisted_proxies = set()
        except sqlite3.Error as e:
            logging.error(f"Error connecting to the database: {e}")
            raise

    def initialize_db(self):
        """Initializes the SQLite database to store proxy information."""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS proxies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    anonymity_level INTEGER,
                    last_checked TIMESTAMP
                )
            ''')
            self.db_conn.commit()
            logging.info("Database initialized successfully.")
        except sqlite3.Error as e:
            logging.error(f"Error initializing the database: {e}")
            raise

    def fetch_proxies(self):
        # Placeholder for proxy fetching logic.
        return []

# EmailExtractor Class
class EmailExtractor:
    def __init__(self):
        # Compile a regular expression for matching email addresses
        self.regexp = re.compile(
            r"""(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"""
        )

    @property
    def name(self) -> str:
        return "email"

    def extract_emails(self, page_source: str) -> set:
        """Extract emails from a string (webpage content)"""
        return {i for i in self.regexp.findall(page_source)}

# Email Harvester Class
class EmailHarvester:
    def __init__(self, use_proxies):
        self.proxy_scanner = ProxyScanner() if use_proxies else None
        self.session = None
        self.use_proxies = use_proxies
        self.extractor = EmailExtractor()  # Add the email extractor here

    async def initialize(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    async def fetch_url_with_playwright(self, url):
        """Use Playwright with stealth mode to scrape JavaScript-heavy websites."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Activate stealth mode
            await stealth_async(page)

            try:
                await page.goto(url)
                await page.wait_for_load_state("networkidle")  # Wait for all network activity to stop
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                emails = self.extractor.extract_emails(str(soup))  # Extract emails using EmailExtractor
                return list(emails)
            except Exception as e:
                logging.error(f"Error fetching page with Playwright: {e}")
                return []
            finally:
                await browser.close()

    async def harvest_emails(self, urls: list, max_depth: int = 2) -> list:
        """Scrape emails from the given list of URLs."""
        all_emails = []
        for url in urls:
            emails = await self.fetch_url_with_playwright(url)
            all_emails.extend(emails)
        return list(set(all_emails))

@st.cache_resource
def get_harvester(use_proxies):
    return EmailHarvester(use_proxies)

# Scheduled scraping task
async def scheduled_scraping():
    harvester = get_harvester(st.session_state.use_proxies)
    await run_scheduled_harvest(harvester)

async def run_scheduled_harvest(harvester):
    await harvester.initialize()
    urls = st.session_state.urls
    emails = await harvester.harvest_emails(urls)
    await harvester.close()
    logging.info(f"Scheduled scraping found {len(emails)} unique emails.")

# Validate and normalize URL
def is_valid_url(url):
    """Check if a URL is valid."""
    try:
        result = urlparse(url)
        return all([result.netloc])  # Allow URLs even if they don't have a scheme
    except ValueError:
        return False

def normalize_url(url):
    """Ensure the URL starts with http:// or https://."""
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        # Default to https:// if no scheme is provided
        return 'https://' + url
    return url

# Main Streamlit App Logic
async def main_async():
    # Toggle proxy usage
    use_proxies = st.sidebar.checkbox("Enable Proxy Usage", value=True)

    harvester = get_harvester(use_proxies)

    st.write("Enter URLs to scrape emails from (one per line):")
    urls_input = st.text_area("URLs")
    max_depth = st.slider("Max Crawl Depth", 0, 5, 2)

    # Sidebar with tools
    st.sidebar.title("🔧 Tools")
    if st.sidebar.button("View Logs"):
        with open('scraper.log') as f:
            st.sidebar.text(f.read())

    # Schedule scraping task
    if st.sidebar.button("Schedule Scraping (Daily at 9 AM)"):
        scheduler.add_job(await scheduled_scraping, 'cron', hour=9, minute=0)
        scheduler.start()
        st.sidebar.success("Scheduled scraping task added.")

    if scheduler.get_jobs():
        st.sidebar.write("Scheduled Jobs:")
        for job in scheduler.get_jobs():
            st.sidebar.write(f"- {job}")
    else:
        st.sidebar.write("No jobs scheduled.")

    # Feedback form
    feedback_text = st.sidebar.text_area("Submit your feedback or report an issue")
    if st.sidebar.button("Submit Feedback"):
        logging.info(f"Feedback submitted: {feedback_text}")
        st.sidebar.success("Thank you for your feedback!")

    # Start harvesting emails
    if st.button("Start Harvesting"):
        # Normalize and validate the URLs
        urls = [normalize_url(url.strip()) for url in urls_input.splitlines() if is_valid_url(normalize_url(url.strip()))]

        if urls:
            with st.spinner('Harvesting emails...'):
                emails = await harvester.harvest_emails(urls, max_depth)

                if emails:
                    st.write(f"Found {len(emails)} unique emails:")
                    email_df = pd.DataFrame(emails, columns=["Email"])
                    st.write(email_df)

                    # Export as CSV
                    csv = email_df.to_csv(index=False).encode('utf-8')
                    st.download_button(label="Download as CSV", data=csv, file_name="harvested_emails.csv", mime="text/csv")

                    # Export as Excel
                    excel_data = BytesIO()
                    email_df.to_excel(excel_data, index=False)
                    st.download_button(label="Download as Excel", data=excel_data.getvalue(), file_name='emails.xlsx',
                                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                else:
                    st.write("No emails found.")
        else:
            st.write("Please enter at least one valid URL.")

# Main function for Streamlit
def main():
    # Streamlit automatically runs its own event loop, no need for asyncio.run().
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
