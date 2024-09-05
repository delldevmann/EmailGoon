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

# Configure logging
logging.basicConfig(filename='scraper.log', level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Streamlit page configuration
st.set_page_config(page_title='Enhanced Email Harvester', page_icon='🌾', layout="wide")
st.title("🌾 Streamlit Cloud Email Harvester")

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
            self.db_conn = sqlite3.connect('proxy_database.db', check_same_thread=False)
            self.initialize_db()
            self.blacklisted_proxies = set()
        except sqlite3.Error as e:
            logging.error(f"Error connecting to the database: {e}")
            raise

    def initialize_db(self):
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
        return []

# EmailExtractor Class
class EmailExtractor:
    def __init__(self):
        # Updated regex for better email extraction
        self.regexp = re.compile(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        )

    def extract_emails(self, page_source: str) -> set:
        """Extract emails from a string (webpage content)"""
        return {i for i in self.regexp.findall(page_source)}

# Email Harvester Class
class EmailHarvester:
    def __init__(self, use_proxies):
        self.proxy_scanner = ProxyScanner() if use_proxies else None
        self.session = None
        self.use_proxies = use_proxies
        self.extractor = EmailExtractor()

    async def initialize(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def fetch_url(self, url):
        """Fetch URL content using aiohttp and extract emails."""
        try:
            async with self.session.get(url) as response:
                logging.info(f"Fetching {url} with status code: {response.status}")
                if response.status != 200:
                    logging.error(f"Failed to fetch {url}: Status {response.status}")
                    return []
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                emails = self.extractor.extract_emails(str(soup))  # Extract emails using EmailExtractor
                return list(emails)
        except Exception as e:
            logging.error(f"Error fetching {url}: {e}")
            return []

    async def harvest_emails(self, urls: list) -> list:
        """Scrape emails from the given list of URLs."""
        all_emails = []
        for url in urls:
            emails = await self.fetch_url(url)
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
        return 'https://' + url
    return url

# Main Streamlit App Logic
async def main_async():
    use_proxies = st.sidebar.checkbox("Enable Proxy Usage", value=True)

    harvester = get_harvester(use_proxies)

    st.write("Enter URLs to scrape emails from (one per line):")
    urls_input = st.text_area("URLs")

    # Sidebar with tools
    st.sidebar.title("🔧 Tools")
    if st.sidebar.button("View Logs"):
        with open('scraper.log') as f:
            st.sidebar.text(f.read())

    # Start harvesting emails
    if st.button("Start Harvesting"):
        urls = [normalize_url(url.strip()) for url in urls_input.splitlines() if is_valid_url(normalize_url(url.strip()))]

        if urls:
            with st.spinner('Harvesting emails...'):
                emails = await harvester.harvest_emails(urls)

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
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
