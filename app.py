import requests
from bs4 import BeautifulSoup
import streamlit as st
import re
import pandas as pd
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from io import BytesIO
from urllib.parse import urljoin

# Setting page configuration
st.set_page_config(page_title='Streamlit Cloud Email Harvester', page_icon='🌾', initial_sidebar_state="auto")
st.title("🌾 Email Harvester")

# Initialize logging
logging.basicConfig(filename='scraper.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Initialize scheduler
scheduler = BackgroundScheduler()

# Initialize session state for batch processing
if 'urls' not in st.session_state:
    st.session_state.urls = []

# Sidebar for managing and scheduling tasks
st.sidebar.title("🔧 Tools")
if st.sidebar.button("View Logs"):
    with open('scraper.log') as f:
        st.sidebar.text(f.read())

def validate_and_format_url(url):
    """Ensure the URL starts with http:// or https://, otherwise prepend https://."""
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

def is_valid_email(email):
    """Check if an email address is valid."""
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.match(regex, email) is not None

def extract_emails(soup):
    """Extract emails from the BeautifulSoup object."""
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', str(soup))
    return list(set([email for email in emails if is_valid_email(email)]))

def find_links(soup, base_url):
    """Find all links on the page and return their absolute URLs."""
    links = set()
    for link in soup.find_all('a', href=True):
        full_url = urljoin(base_url, link['href'])
        links.add(full_url)
    return links

def scrape_emails_from_url(url, depth, visited):
    """Scrape emails from a single URL and crawl deeper."""
    if depth < 0 or url in visited:
        return []

    visited.add(url)
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        emails = extract_emails(soup)
        logging.info(f"Successfully scraped {len(emails)} emails from {url}")
        
        # Find links to crawl deeper
        links = find_links(soup, url)
        for link in links:
            emails += scrape_emails_from_url(link, depth - 1, visited)  # Recursively scrape linked pages

        return emails
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to scrape {url}: {e}")
        return []

# Text area for multiple URLs and depth selection
urls_input = st.text_area("Enter URLs to scrape emails from (one per line)")
depth_input = st.number_input("Crawl Depth (0 for only the specified URLs)", min_value=0, value=1)

if st.button("Start Scraping"):
    st.session_state.urls = [validate_and_format_url(url.strip()) for url in urls_input.splitlines() if url.strip()]
    all_emails = []
    visited_urls = set()  # Track visited URLs
    progress_bar = st.progress(0)

    total_urls = len(st.session_state.urls)
    for i, url in enumerate(st.session_state.urls):
        st.write(f"Scraping: {url}")
        emails = scrape_emails_from_url(url, depth_input, visited_urls)
        all_emails.extend(emails)
        progress_bar.progress((i + 1) / total_urls)

    all_emails = list(set(all_emails))  # Remove duplicates
    st.write(f"Found {len(all_emails)} unique emails.")

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

# Feedback form
st.sidebar.title("Feedback")
feedback_text = st.sidebar.text_area("Submit your feedback or report an issue")
if st.sidebar.button("Submit Feedback"):
    logging.info(f"Feedback submitted: {feedback_text}")
    st.sidebar.success("Thank you for your feedback!")

# Scheduled scraping task
def scheduled_scraping():
    visited = set()
    for url in st.session_state.urls:
        emails = scrape_emails_from_url(url, depth_input, visited)
    all_emails = list(set(emails))
    logging.info(f"Scheduled task found {len(all_emails)} unique emails.")

if st.sidebar.button("Schedule Scraping (Daily at 9 AM)"):
    scheduler.add_job(scheduled_scraping, 'cron', hour=9, minute=0)
    scheduler.start()
    st.sidebar.success("Scheduled scraping task added.")

# Display current jobs
if scheduler.get_jobs():
    st.sidebar.write("Scheduled Jobs:")
    for job in scheduler.get_jobs():
        st.sidebar.write(f"- {job}")
else:
    st.sidebar.write("No jobs scheduled.")
