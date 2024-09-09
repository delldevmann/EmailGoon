import asyncio
import re
from urllib.parse import urljoin, urlparse
from typing import List, Set
import aiohttp
from aiohttp import ClientSession, ClientError, ClientTimeout
from bs4 import BeautifulSoup

class EmailHarvester:
    def __init__(self, max_concurrent_requests: int = 10):
        # Set to track visited URLs and avoid scraping the same page multiple times
        self.visited_urls: Set[str] = set()
        # Regex pattern to find email addresses
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', re.IGNORECASE)
        # Semaphore to control the number of concurrent requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def fetch_url(self, session: ClientSession, url: str) -> str:
        """Fetch HTML content of a URL asynchronously."""
        try:
            # Using semaphore to limit concurrent requests
            async with self.semaphore:
                async with session.get(url, timeout=ClientTimeout(total=10)) as response:
                    response.raise_for_status()  # Raise exception for bad status codes
                    return await response.text()
        except ClientError as e:
            print(f"Error fetching {url}: {e}")
            return ""

    def extract_emails(self, html_content: str) -> Set[str]:
        """Extract email addresses from the HTML content using regex."""
        return set(self.email_pattern.findall(html_content))

    def extract_links(self, html_content: str, base_url: str) -> Set[str]:
        """Extract all the valid links from the HTML content and make them absolute."""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(base_url, href)
            # Only return links within the same domain
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                links.add(full_url)
        return links

    async def crawl(self, url: str, max_depth: int = 2) -> Set[str]:
        """Recursively scrape emails from a URL and its linked pages up to a certain depth."""
        if max_depth < 0 or url in self.visited_urls:
            return set()

        self.visited_urls.add(url)
        emails = set()

        # Start a client session
        async with ClientSession() as session:
            # Fetch the page content
            html_content = await self.fetch_url(session, url)
            if html_content:
                # Extract emails from the current page
                emails.update(self.extract_emails(html_content))

                # If the depth allows, extract links and recursively crawl them
                if max_depth > 0:
                    links = self.extract_links(html_content, url)
                    tasks = [self.crawl(link, max_depth - 1) for link in links]
                    results = await asyncio.gather(*tasks)
                    for result in results:
                        emails.update(result)

        return emails

    async def harvest_emails(self, urls: List[str], max_depth: int = 2) -> Set[str]:
        """Start the email harvesting process by crawling multiple URLs."""
        tasks = [self.crawl(url, max_depth) for url in urls]
        results = await asyncio.gather(*tasks)
        return set.union(*results)

# Main function to start the email harvester
async def main():
    harvester = EmailHarvester(max_concurrent_requests=10)  # Adjust the concurrency limit if needed
    urls = [
        "https://example.com",
        "https://example.org"
    ]
    # Start harvesting emails from the given URLs
    emails = await harvester.harvest_emails(urls, max_depth=2)
    
    # Output the results
    print(f"Found {len(emails)} unique emails:")
    for email in sorted(emails):
        print(email)

# Run the asynchronous main function
if __name__ == "__main__":
    asyncio.run(main())
