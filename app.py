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

# Set page configuration
st.set_page_config(page_title='Email Harvester', page_icon='📧', initial_sidebar_state="expanded")

# Add the image
st.markdown(
    """
    <div style='text-align:center;'>
        <img src='https://raw.githubusercontent.com/delldevmann/EmailGoon/main/2719aef3-8bc0-42cb-ae56-6cc2c791763f-removebg-preview.png' alt='Email Harvester' width='150'>
    </div>
    """,
    unsafe_allow_html=True
)

# Title
st.title("📧 Email Harvester")

# Introduction text
st.write("This tool allows you to validate proxies and scrape emails. The grid layout helps you access and view multiple functionalities at once.")

# Create a two-column layout
col1, col2 = st.columns(2)

# Column 1: Proxy Validation
with col1:
    st.subheader("Step 1: Validate Proxies")

    async def test_proxy(proxy, session):
        test_url = "http://www.google.com"
        try:
            async with session.get(test_url, proxy=f"http://{proxy}", timeout=5) as response:
                return response.status == 200
        except:
            return False

    async def get_proxy_geolocation(proxy):
        ip = proxy.split(':')[0]
        api_url = f"https://ipinfo.io/{ip}/json"
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

    async def fetch_free_proxies():
        proxy_sources = [
            'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
            'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
        ]
        selected_source = random.choice(proxy_sources)
        async with aiohttp.ClientSession() as session:
            async with session.get(selected_source) as response:
                proxy_list = await response.text()
                proxies = proxy_list.splitlines()[:10]
                tasks = []
                for proxy in proxies:
                    tasks.append(
                        asyncio.gather(test_proxy(proxy, session), get_proxy_geolocation(proxy))
                    )

                results = await asyncio.gather(*tasks)

                proxy_details = []
                for i, (is_working, geo_info) in enumerate(results):
                    proxy_details.append({
                        'proxy': proxies[i],
                        'is_working': is_working,
                        'ip': geo_info['ip'],
                        'city': geo_info['city'],
                        'country': geo_info['country'],
                    })

                return proxy_details

    proxy_results = st.session_state.get('proxy_results', None)

    if st.button("Validate Proxies"):
        try:
            with st.spinner("Fetching and validating proxies..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                st.session_state['proxy_results'] = loop.run_until_complete(fetch_free_proxies())
                proxy_results = st.session_state['proxy_results']

            if proxy_results:
                st.success("Proxies validated successfully!")
                proxy_df = pd.DataFrame(proxy_results)
                proxy_df['status'] = proxy_df['is_working'].apply(lambda x: 'Working' if x else 'Not Working')
                st.table(proxy_df[['ip', 'city', 'country', 'status']])
            else:
                st.info("No proxies found.")
        except Exception as e:
            st.error(f"An error occurred: {e}")

# Column 2: Scrape Emails
with col2:
    st.subheader("Step 2: Scrape Emails")

    selected_proxy = st.session_state.get('selected_proxy', None)
    if selected_proxy:
        st.success(f"Selected Proxy: {selected_proxy}")
    else:
        st.warning("Please validate proxies first and select one.")

    urls_input = st.text_area("Enter URLs (one per line):")
    depth = st.number_input("Enter Crawl Depth (0 for no recursion)", min_value=0, value=1)

    if st.button("Start Scraping"):
        if urls_input.strip() and selected_proxy:
            st.success(f"Scraping started using proxy: {selected_proxy}")

# Footer Disclaimer
st.write("⚠️ **Please ensure you have permission to scrape data from websites and comply with local regulations.**")
