import asyncio
import re
from urllib.parse import urljoin, urlparse
from typing import List, Set
import aiohttp
from aiohttp import ClientSession, ClientError, ClientTimeout
from bs4 import BeautifulSoup

class EmailHarvester:
    def __init__(self, max_concurrent_requests: int = 10):
        self.visited_urls: Set[str] = set()
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', re.IGNORECASE)
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)  # Limit concurrency

    async def fetch_url(self, session: ClientSession, url: str) -> str:
        try:
            async with self.semaphore:  # Limit concurrent requests
                async with session.get(url, timeout=ClientTimeout(total=10)) as response:
                    return await response.text()
        except ClientError as e:
            print(f"Error fetching {url}: {e}")
            return ""

    def extract_emails(self, html_content: str) -> Set[str]:
        return set(self.email_pattern.findall(html_content))

    def extract_links(self, html_content: str, base_url: str) -> Set[str]:
        soup = BeautifulSoup(html_content, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(base_url, href)
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                links.add(full_url)
        return links

    async def crawl(self, url: str, max_depth: int = 2) -> Set[str]:
        if max_depth < 0 or url in self.visited_urls:
            return set()

        self.visited_urls.add(url)
        emails = set()

        async with ClientSession() as session:
            html_content = await self.fetch_url(session, url)
            if html_content:
                emails.update(self.extract_emails(html_content))

                if max_depth > 0:
                    links = self.extract_links(html_content, url)
                    tasks = [self.crawl(link, max_depth - 1) for link in links]
                    results = await asyncio.gather(*tasks)
                    for result in results:
                        emails.update(result)

        return emails

    async def harvest_emails(self, urls: List[str], max_depth: int = 2) -> Set[str]:
        tasks = [self.crawl(url, max_depth) for url in urls]
        results = await asyncio.gather(*tasks)
        return set.union(*results)

async def main():
    harvester = EmailHarvester(max_concurrent_requests=10)
    urls = [
        "https://example.com",
        "https://example.org"
    ]
    emails = await harvester.harvest_emails(urls, max_depth=2)
    print(f"Found {len(emails)} unique emails:")
    for email in sorted(emails):
        print(email)

if __name__ == "__main__":
    asyncio.run(main())
