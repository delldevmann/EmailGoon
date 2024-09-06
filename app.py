import asyncio
import aiohttp
from bs4 import BeautifulSoup
import streamlit as st
import re
import pandas as pd
import logging
from io import BytesIO
from urllib.parse import urljoin
import random

# Setting page configuration
st.set_page_config(page_title='Streamlit Cloud Email Harvester', page_icon='🌾', initial_sidebar_state="auto")
st.title("🌾 Email Harvester")

# Initialize logging
logging.basicConfig(filename='scraper.log', level=logging.INFO, format='%(asctime)s - %(message)s')  # Log all info and above

# Initialize session state for batch processing
if 'urls' not in st.session_state:
    st.session_state.urls = []

# Sidebar for managing and scheduling tasks
st.sidebar.title("🔧 Tools")
if st.sidebar.button("View Logs"):
    with open('scraper.log') as f:
        st.sidebar.text(f.read())

# User-Agent list
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/60.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 10; Pixel 3 XL Build/QQ1A.200205.002) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Mobile Safari/537.36"
]

# Limiting concurrent requests to avoid overloading
MAX_CONCURRENT_REQUESTS = 10

def validate_and_format_url(url):
    """Ensure the URL starts with http:// or https://, otherwise prepend https://."""
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

def is_valid_email(email):
    """Check if an email address is valid."""
    regex = r'(?i)(?<!\w)([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z]{2,})(?!\w)'
    return re.match(regex, email) is not None

def extract_emails(soup):
    """Extract emails from the BeautifulSoup object."""
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', str(soup))
    return list(set(email for email in emails if is_valid_email(email)))

def find_links(soup, base_url):
    """Find all links on the page and return their absolute URLs within the same domain."""
    base_domain = re.match(r"https?://(www\.)?([^/]+)", base_url).group(2)
    links = set()
    for link in soup.find_all('a', href=True):
        full_url = urljoin(base_url, link['href'])
        if base_domain in full_url:  # Ensure we're staying within the same domain
            links.add(full_url)
    return links

async def fetch_url(session, url, semaphore):
    """Fetch a single URL and extract emails."""
    headers = {'User-Agent': random.choice(USER_AGENTS)}  # Random User-Agent
    try:
        async with semaphore:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    return extract_emails(soup), find_links(soup, url)
                else:
                    logging.warning(f"Failed to fetch {url}: Status {response.status}")
                    return [], []
    except asyncio.TimeoutError:
        logging.error(f"Timeout fetching {url}")
        return [], []
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return [], []

async def scrape_emails_from_url(session, url, depth, visited, semaphore, status_placeholder):
    """Scrape emails from a URL and crawl deeper."""
    if depth < 0 or url in visited:
        return []

    visited.add(url)
    emails = []
    status_placeholder.text(f"Scraping {url}...")
    extracted_emails, found_links = await fetch_url(session, url, semaphore)
    emails.extend(extracted_emails)

    # Recursively scrape found links
    for link in found_links:
        if link not in visited:
            emails.extend(await scrape_emails_from_url(session, link, depth - 1, visited, semaphore, status_placeholder))

    return emails

async def scrape_emails_from_urls(urls, depth, status_placeholder):
    """Scrape emails from multiple URLs concurrently."""
    visited = set()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_emails_from_url(session, url, depth, visited, semaphore, status_placeholder) for url in urls]
        results = await asyncio.gather(*tasks)
        return [email for sublist in results for email in sublist]  # Flatten the list of lists

# Main Streamlit App Logic
async def main_async():
    # Text area for multiple URLs and depth selection
    urls_input = st.text_area("Enter URLs to scrape emails from (one per line)")
    depth_input = st.number_input("Crawl Depth (0 for only the specified URLs)", min_value=0, value=1)

    if st.button("Start Scraping"):
        st.session_state.urls = [validate_and_format_url(url.strip()) for url in urls_input.splitlines() if url.strip()]
        all_emails = []
        status_placeholder = st.empty()  # Placeholder for dynamic status updates
        progress_bar = st.progress(0)

        total_urls = len(st.session_state.urls)
        if total_urls > 0:
            with st.spinner('Harvesting emails...'):
                for i, url in enumerate(st.session_state.urls):
                    emails = await scrape_emails_from_urls([url], depth_input, status_placeholder)
                    all_emails.extend(emails)
                    progress_bar.progress((i + 1) / total_urls)

                all_emails = list(set(all_emails))  # Remove duplicates
                status_placeholder.text(f"Finished scraping. Found {len(all_emails)} unique emails.")

                if all_emails:
                    email_df = pd.DataFrame(all_emails, columns=["Email"])
                    st.write(email_df)

                    # Export as CSV
                    csv_data = email_df.to_csv(index=False).encode('utf-8')
                    st.download_button(label="Download as CSV", data=csv_data, file_name='emails.csv', mime='text/csv')

                    # Export as Excel
                    excel_data = BytesIO()
                    email_df.to_excel(excel_data, index=False)
                    st.download_button(label="Download as Excel", data=excel_data.getvalue(), file_name='emails.xlsx',
                                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        else:
            st.write("Please enter at least one valid URL.")

# Main function for Streamlit
def main():
    # Streamlit automatically runs its own event loop, no need for asyncio.run().
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
