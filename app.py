import requests
from bs4 import BeautifulSoup
import streamlit as st
import re
import pandas as pd
from urllib.parse import urljoin

# Set up page configuration
st.set_page_config(page_title='Recursive Email Scraper', page_icon='🌾', initial_sidebar_state="auto")
st.title("🌾 Recursive Email Scraper")

def validate_and_format_url(url):
    """Ensure the URL starts with http:// or https://, otherwise prepend https://."""
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

def extract_emails(soup):
    """Extract email addresses from the HTML content using regex."""
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_regex, str(soup))
    return set(emails)  # Return a set to avoid duplicates

def find_links(soup, base_url):
    """Extract and return absolute links from the page."""
    links = set()
    for a_tag in soup.find_all("a", href=True):
        url = urljoin(base_url, a_tag['href'])
        if url.startswith(('http://', 'https://')):
            links.add(url)
    return links

def scrape_emails_recursive(url, depth, visited):
    """Recursively scrape emails from a URL and its linked pages up to a certain depth."""
    if depth < 0 or url in visited:
        return set()  # Return an empty set if depth is 0 or URL is already visited

    visited.add(url)  # Mark URL as visited
    emails = set()  # To store all the found emails
    
    try:
        # Fetch the page content
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract emails from the current page
        emails.update(extract_emails(soup))

        # Recursively scrape links found on the current page
        links = find_links(soup, url)
        for link in links:
            emails.update(scrape_emails_recursive(link, depth - 1, visited))

    except requests.RequestException as e:
        st.error(f"Error fetching the URL: {url}. {e}")
    
    return emails

# Input for the URL and crawl depth
url = st.text_input("Enter URL to scrape emails from", "https://stan.store/brydon")
depth = st.number_input("Enter Crawl Depth (0 for no recursion)", min_value=0, value=1)

# Button to start scraping
if st.button("Start Scraping"):
    if url.strip():  # Ensure the URL is not empty
        url = validate_and_format_url(url.strip())  # Validate and format URL
        visited = set()  # Set to keep track of visited URLs
        
        try:
            # Show progress spinner while scraping
            with st.spinner("Scraping emails..."):
                # Start recursive email scraping
                all_emails = scrape_emails_recursive(url, depth, visited)
                
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
                    st.info("No emails found on the page.")
        except Exception as e:
            st.error(f"Error occurred: {e}")
    else:
        st.warning("Please enter a valid URL.")

# Disclaimer
st.warning("⚠️ Warning: Note that not all websites may contain email addresses or allow email harvesting. Harvesting email addresses without permission may be a violation of the website's terms of service or applicable laws. Be sure to read and understand the website's terms of service and any applicable laws or regulations before scraping any website.")
