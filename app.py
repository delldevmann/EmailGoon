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
st.title("📧 Email Harvester - Wizard Interface")

# Introduction text
st.write("Follow the steps below to validate proxies and scrape emails. You must complete each step before proceeding to the next.")

# Step 1: Validate Proxies
if "step_1_completed" not in st.session_state:
    st.session_state['step_1_completed'] = False

if not st.session_state['step_1_completed']:
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
