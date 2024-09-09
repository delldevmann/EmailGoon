import asyncio
import re
from urllib.parse import urljoin, urlparse
from typing import List, Set

import aiohttp
from bs4 import BeautifulSoup
import chardet  # To detect encoding
import streamlit as st
import pandas as pd

class EmailHarvester:
    def __init__(self):
        self.visited_urls: Set[str] = set()
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

    async def fetch_url(self, session: aiohttp.ClientSession, url: str) -> str:
        """Fetch a URL's content asynchronously with proper encoding handling."""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        try:
            async with session.get(url, headers=headers) as response:
                # Read the raw bytes of the response
                raw_content = await response.content.read()

                # Detect the encoding using chardet
                detected_encoding = chardet.detect(raw_content)['encoding']
                if detected_encoding is None:
                    detected_encoding = 'utf-8'  # Fallback to utf-8 if detection fails

                # Decode using the detected encoding
                return raw_content.decode(detected_encoding, errors='replace')
        except aiohttp.ClientError as e:
            st.warning(f"Error fetching {url}: {e}")
            return ""

    def extract_emails(self, html_content: str) -> Set[str]:
        """Extract emails using regex from HTML content."""
        return set(self.email_pattern.findall(html_content))

    def extract_links(self, html_content: str, base_url: str) -> Set[str]:
        """Extract links from the HTML content and return absolute URLs."""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(base_url, href)
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                links.add(full_url)
        return links

    async def crawl(self, url: str, max_depth: int = 2) -> Set[str]:
        """Crawl a URL recursively up to a max depth."""
        if max_depth < 0 or url in self.visited_urls:
            return set()

        self.visited_urls.add(url)
        emails = set()

        async with aiohttp.ClientSession() as session:
            try:
                html_content = await self.fetch_url(session, url)
                emails.update(self.extract_emails(html_content))

                if max_depth > 0:
                    links = self.extract_links(html_content, url)
                    tasks = [self.crawl(link, max_depth - 1) for link in links]
                    results = await asyncio.gather(*tasks)
                    for result in results:
                        emails.update(result)
            except aiohttp.ClientError:
                st.warning(f"Error fetching {url}")

        return emails

    async def harvest_emails(self, urls: List[str], max_depth: int = 2) -> Set[str]:
        """Harvest emails from multiple URLs concurrently."""
        tasks = [self.crawl(url, max_depth) for url in urls]
        results = await asyncio.gather(*tasks)
        return set.union(*results)

def validate_and_format_url(url: str) -> str:
    """Ensure the URL starts with http:// or https://. If not, prepend https://."""
    parsed_url = urlparse(url)
    if not parsed_url.scheme:  # If no scheme, assume https
        return "https://" + url
    return url

async def main_async(urls: List[str], max_depth: int):
    """Main async function to start the email harvester."""
    harvester = EmailHarvester()
    emails = await harvester.harvest_emails(urls, max_depth)
    return emails

# Streamlit app
st.set_page_config(page_title='Email Harvester', page_icon='📧', initial_sidebar_state="auto")
st.title("🌾🚜 Cloud Email Harvester")

# Input URL
urls_input = st.text_area("Enter URLs to scrape emails from (one per line)")
depth = st.number_input("Enter Crawl Depth (0 for no recursion)", min_value=0, value=1)

# Convert the input into a list of URLs and validate them
urls = [validate_and_format_url(url.strip()) for url in urls_input.splitlines() if url.strip()]

# Button to start scraping
if st.button("Start Scraping"):
    if urls:
        try:
            # Show progress spinner while scraping
            with st.spinner("Scraping emails..."):
                # Run the asynchronous scraping function
                all_emails = asyncio.run(main_async(urls, depth))
                
                if all_emails:
                    st.success(f"Found {len(all_emails)} unique email(s):")
                    st.write(list(all_emails))
                    
                    # Convert email set to DataFrame for CSV download
                    email_df = pd.DataFrame(list(all_emails), columns=["Email"])
                    
                    # Download button for CSV
                    csv = email_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download as CSV",
                        data=csv,
                        file_name='emails.csv',
                        mime='text/csv'
                    )
                else:
                    st.info("No emails found on the pages.")
        except Exception as e:
            st.error(f"Error occurred: {e}")
    else:
        st.warning("Please enter at least one valid URL.")

# Disclaimer
st.warning("⚠️ Warning: Some websites may restrict scraping. Ensure you have permission to scrape data and comply with local regulations.")
