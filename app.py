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

# Set page configuration at the top of the file
st.set_page_config(page_title='Email Harvester', page_icon='📧', initial_sidebar_state="expanded")

# Add custom CSS to update layout and design
st.markdown(
    """
    <style>
    .custom-image {
        margin-bottom: -50px;
        display: flex;
        justify-content: center;
    }
    .proxy-table th, .proxy-table td {
        padding: 10px;
        text-align: center;
    }
    .proxy-table {
        border: 1px solid #ddd;
        border-collapse: collapse;
        width: 100%;
    }
    .proxy-table th {
        background-color: #f2f2f2;
    }
    .status-green {
        color: green;
        font-weight: bold;
    }
    .status-red {
        color: red;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True
)

# Use st.markdown() with raw HTML to insert the image and apply the CSS class
st.markdown(
    """
    <div class="custom-image">
        <img src='https://raw.githubusercontent.com/delldevmann/EmailGoon/main/2719aef3-8bc0-42cb-ae56-6cc2c791763f-removebg-preview.png' alt='Email Harvester' width='200px'>
    </div>
    """,
    unsafe_allow_html=True
)

# Proxy logic and functions are retained from the previous code but updated for dynamic feedback
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
            proxies = proxy_list.splitlines()[:10]  # Limit to 10 proxies for faster demo
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

# Streamlit app interface for proxy validation
st.subheader("Step 1: Validate Proxies")
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
            proxy_df['status'] = proxy_df['is_working'].apply(lambda x: '🟢 Working' if x else '🔴 Not Working')
            
            # Display updated table with color-coded status
            st.markdown("""
                <table class="proxy-table">
                    <thead>
                        <tr>
                            <th>IP</th>
                            <th>City</th>
                            <th>Country</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                """, unsafe_allow_html=True)

            for index, row in proxy_df.iterrows():
                status_class = "status-green" if row['status'] == '🟢 Working' else "status-red"
                st.markdown(f"""
                    <tr>
                        <td>{row['ip']}</td>
                        <td>{row['city']}</td>
                        <td>{row['country']}</td>
                        <td class="{status_class}">{row['status']}</td>
                    </tr>
                """, unsafe_allow_html=True)

            st.markdown("</tbody></table>", unsafe_allow_html=True)
        else:
            st.info("No proxies found.")
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Section 2: Choose Proxy and Start Scraping
if proxy_results:
    with st.expander("Step 2: Choose a Proxy and Start Scraping", expanded=True):
        st.subheader("Choose a Proxy")
        working_proxies = [f"{p['proxy']} ({p['city']}, {p['country']})" for p in proxy_results if p['is_working']]
        selected_proxy_display = st.selectbox("Select a Proxy", working_proxies, key='selected_proxy_display')
        if selected_proxy_display:
            st.session_state['selected_proxy'] = selected_proxy_display.split()[0]
            selected_proxy = st.session_state['selected_proxy']
        if selected_proxy:
            st.success(f"Selected Proxy: {selected_proxy_display}")
            st.info(f"Using proxy: {selected_proxy}")

        st.subheader("Enter URLs for Scraping")
        urls_input = st.text_area("Enter URLs (one per line):")
        depth = st.number_input("Enter Crawl Depth (0 for no recursion)", min_value=0, value=1)

        if st.button("Start Scraping"):
            if urls_input.strip() and selected_proxy:
                st.success(f"Scraping started using proxy: {selected_proxy}")

# Disclaimer
st.warning("⚠️ Please ensure you have permission to scrape data from websites and comply with local regulations.")
