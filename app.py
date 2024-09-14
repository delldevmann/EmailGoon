import asyncio
import random
import re
from urllib.parse import urljoin, urlparse
from typing import List, Set, Dict
import aiohttp
from bs4 import BeautifulSoup
import chardet  # To detect encoding
import streamlit as st
import pandas as pd

# Function to get the geolocation of a proxy IP
async def get_proxy_geolocation(proxy):
    ip = proxy.split(':')[0]  # Get the IP part of the proxy
    api_url = f"https://ipinfo.io/{ip}/json"  # Using ipinfo.io API for geolocation
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'ip': ip,
                        'city': data.get('city', 'Unknown'),
                        'country': data.get('country', 'Unknown')
                    }
                else:
                    return {'ip': ip, 'city': 'Unknown', 'country': 'Unknown'}
    except Exception as e:
        return {'ip': ip, 'city': 'Unknown', 'country': 'Unknown', 'error': str(e)}

# Test if a proxy is working by making a request to a known website
async def test_proxy(proxy):
    test_url = "http://www.google.com"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url, proxy=f"http://{proxy}", timeout=5) as response:
                if response.status == 200:
                    return True
    except:
        return False

# Fetch proxies from multiple GitHub sources (list of public proxies)
async def fetch_free_proxies():
    proxy_sources = [
        'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
        'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
        'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/proxy.txt',
        'https://raw.githubusercontent.com/a2u/free-proxy-list/main/free-proxy-list.txt',
        'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
        'https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt',
        'https://raw.githubusercontent.com/mertguvencli/http-proxy-list/main/proxy-list/data.txt',
        'https://raw.githubusercontent.com/jenssegers/proxy-list/main/proxies.txt',
        'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt',
        'https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt',
    ]

    # Randomly choose a source and fetch the proxy list
    selected_source = random.choice(proxy_sources)
    async with aiohttp.ClientSession() as session:
        async with session.get(selected_source) as response:
            proxy_list = await response.text()
            proxies = proxy_list.splitlines()[:20]

            # Gather all tasks for testing proxies and getting geolocation
            tasks = []
            for proxy in proxies:
                tasks.append(asyncio.gather(test_proxy(proxy), get_proxy_geolocation(proxy)))

            results = await asyncio.gather(*tasks)

            # Combine test results and geolocation data
            proxy_details = []
            for i, (is_working, geo_info) in enumerate(results):
                proxy_details.append({
                    'proxy': proxies[i],
                    'is_working': is_working,
                    'ip': geo_info['ip'],
                    'city': geo_info['city'],
                    'country': geo_info['country']
                })

            return proxy_details

# Define the Email Harvester class
class EmailHarvester:
    def __init__(self, proxies=None, selected_proxy=None):
        self.visited_urls: Set[str] = set()
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.errors: Dict[str, str] = {}  # Dictionary to store errors
        self.selected_proxy = selected_proxy  # User-selected proxy

    async def fetch_url(self, session: aiohttp.ClientSession, url: str) -> str:
        """Fetch a URL's content asynchronously with proper encoding handling."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        try:
            async with session.get(url, headers=headers, proxy=f"http://{self.selected_proxy}" if self.selected_proxy else None) as response:
                raw_content = await response.content.read()

                # Detect the encoding using chardet
                detected_encoding = chardet.detect(raw_content)['encoding']
                if detected_encoding is None:
                    detected_encoding = 'utf-8'  # Fallback to utf-8 if detection fails

                return raw_content.decode(detected_encoding, errors='replace')
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.errors[url] = f"{type(e).__name__}: {str(e)}"
            return ""

    def extract_emails(self, html_content: str) -> Set[str]:
        """Extract emails using regex from HTML content."""
        if html_content:  # Ensure we are not working with empty content
            return set(self.email_pattern.findall(html_content))
        return set()

    def extract_links(self, html_content: str, base_url: str) -> Set[str]:
        """Extract links from the HTML content and return absolute URLs."""
        if not html_content:
            return set()

        soup = BeautifulSoup(html_content, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(base_url, href)
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                links.add(full_url)
        return links

    async def crawl(self, session: aiohttp.ClientSession, url: str, max_depth: int = 2) -> Set[str]:
        """Crawl a URL recursively up to a max depth."""
        if max_depth < 0 or url in self.visited_urls:
            return set()

        self.visited_urls.add(url)
        emails = set()

        html_content = await self.fetch_url(session, url)
        emails.update(self.extract_emails(html_content))

        if max_depth > 0:
            links = self.extract_links(html_content, url)
            tasks = [self.crawl(session, link, max_depth - 1) for link in links]
            results = await asyncio.gather(*tasks)
            for result in results:
                emails.update(result)

        return emails

    async def harvest_emails(self, urls: List[str], max_depth: int = 2) -> Set[str]:
        """Harvest emails from multiple URLs concurrently."""
        async with aiohttp.ClientSession() as session:
            tasks = [self.crawl(session, url, max_depth) for url in urls]
            results = await asyncio.gather(*tasks)
        return set.union(*results)

# Function to validate URLs
def validate_and_format_url(url: str) -> str:
    """Ensure the URL starts with http:// or https://. If not, prepend https://."""
    parsed_url = urlparse(url)
    if not parsed_url.scheme:  # If no scheme, assume https
        return "https://" + url
    return url

# Async main function
async def main_async(urls: List[str], max_depth: int, selected_proxy: str):
    """Main async function to start the email harvester."""
    harvester = EmailHarvester(selected_proxy=selected_proxy)
    emails = await harvester.harvest_emails(urls, max_depth)
    return emails, harvester.errors  # Return errors if any

# Streamlit app interface
st.set_page_config(page_title='Email Harvester', page_icon='📧', initial_sidebar_state="auto")
st.title("🌾🚜 Cloud Email Harvester with Proxy Dashboard")

# Section 1: Proxy Validation
st.subheader("Step 1: Validate Proxies")
proxy_results = None
if st.button("Validate Proxies"):
    try:
        with st.spinner("Fetching and validating proxies..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            proxy_results = loop.run_until_complete(fetch_free_proxies())

        # Display Proxy Dashboard
        if proxy_results:
            st.success("Proxies validated successfully!")
            proxy_df = pd.DataFrame(proxy_results)
            proxy_df['status'] = proxy_df['is_working'].apply(lambda x: '🟢 Working' if x else '🔴 Not Working')
            st.write(proxy_df[['ip', 'city', 'country', 'status']])
        else:
            st.info("No proxies found.")

    except Exception as e:
        st.error(f"An error occurred: {e}")

# Section 2: Select Proxy and Scraping
if proxy_results:
    with st.expander("Step 2: Choose a Proxy and Start Scraping", expanded=True):
        st.subheader("Choose a Proxy")
        working_proxies = [f"{p['proxy']} ({p['city']}, {p['country']})" for p in proxy_results if p['is_working']]
        selected_proxy = st.selectbox("Select a Proxy", working_proxies)

        st.subheader("Enter URLs for Scraping")
        urls_input = st.text_area("Enter URLs (one per line):")
        depth = st.number_input("Enter Crawl Depth (0 for no recursion)", min_value=0, value=1)

        if st.button("Start Scraping"):
            if urls_input.strip() and selected_proxy:
                urls = [validate_and_format_url(url.strip()) for url in urls_input.splitlines() if url.strip()]
                
                try:
                    with st.spinner("Scraping emails..."):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        all_emails, errors = loop.run_until_complete(main_async(urls, depth, selected_proxy.split()[0]))

                    # Display Results
                    if all_emails:
                        st.success(f"Found {len(all_emails)} unique email(s):")
                        st.write(list(all_emails))
                        
                        # Convert emails to DataFrame for CSV download
                        email_df = pd.DataFrame(list(all_emails), columns=["Email"])
                        csv = email_df.to_csv(index=False).encode('utf-8')

                        # CSV and JSON Download
                        st.download_button(label="Download Emails as CSV", data=csv, file_name='emails.csv', mime='text/csv')

                        json_emails = email_df.to_json(orient='records', lines=True)
                        st.download_button(label="Download Emails as JSON", data=json_emails, file_name='emails.json', mime='application/json')

                    else:
                        st.info("No emails found on the pages.")

                    # Display Errors if any
                    if errors:
                        st.error("Errors encountered:")
                        st.write(errors)

                except Exception as e:
                    st.error(f"An error occurred: {e}")
            else:
                st.warning("Please enter at least one URL and select a proxy.")

# Disclaimer about scraping policies
st.warning("⚠️ Please ensure you have permission to scrape data from websites and comply with local regulations.")
