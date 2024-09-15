import asyncio
import random
import re
import time
from urllib.parse import urljoin, urlparse
from typing import List, Set, Dict
import aiohttp
from bs4 import BeautifulSoup
import chardet
import streamlit as st
import pandas as pd
from aiolimiter import AsyncLimiter
from concurrent.futures import ThreadPoolExecutor

# Set Streamlit page config (make sure this is the first Streamlit command)
st.set_page_config(page_title='Email Harvester', page_icon='📧', initial_sidebar_state="auto")

# Add the image after setting the page config
st.image("https://raw.githubusercontent.com/delldevmann/EmailGoon/main/2719aef3-8bc0-42cb-ae56-6cc2c791763f-removebg-preview.png", width=300)

# In-memory data structures for storing proxy status and cool-off periods
proxy_failure_counts = {}
cool_off_proxies = {}
working_proxies = []
proxy_sources_reputation = {}
cool_off_duration = 600  # Cool-off period in seconds (10 minutes)
max_failures_before_cool_off = 3

# Rate limiter (5 requests per second)
limiter = AsyncLimiter(max_rate=5, time_period=1)

# Check cool-off period for a proxy
def check_cool_off(proxy):
    if proxy in cool_off_proxies:
        if time.time() - cool_off_proxies[proxy] > cool_off_duration:
            del cool_off_proxies[proxy]  # Remove from cool-off if time has passed
            return True
        return False
    return True

# Function to save working proxies to a file
def save_working_proxies(proxies):
    if proxies:
        proxy_df = pd.DataFrame(proxies)
        proxy_df['status'] = proxy_df['is_working'].apply(lambda x: '🟢 Working' if x else '🔴 Not Working')
        csv = proxy_df[proxy_df['is_working'] == True][['ip', 'city', 'country', 'status']].to_csv(index=False)
        st.download_button(label="Download Working Proxies as CSV", data=csv, file_name="working_proxies.csv", mime="text/csv")
    else:
        st.info("No working proxies to save.")

# Proxy validation logic with source reputation tracking
async def validate_proxies(proxy_list, source):
    validated_proxies = []
    total_proxies = len(proxy_list)
    success_count = 0
    async with aiohttp.ClientSession() as session:
        tasks = []
        for proxy in proxy_list:
            # Check if proxy is in cool-off period
            if proxy in proxy_failure_counts and proxy_failure_counts[proxy] >= max_failures_before_cool_off and not check_cool_off(proxy):
                continue
            tasks.append(test_proxy(session, proxy))

        results = await asyncio.gather(*tasks)

        for i, (is_working, geo_info) in enumerate(results):
            proxy = proxy_list[i]
            if is_working:
                validated_proxies.append(geo_info)
                # Reset failure count for working proxies
                proxy_failure_counts[proxy] = 0
                working_proxies.append(proxy)
                success_count += 1
            else:
                # Increment failure count
                if proxy in proxy_failure_counts:
                    proxy_failure_counts[proxy] += 1
                else:
                    proxy_failure_counts[proxy] = 1
                if proxy_failure_counts[proxy] >= max_failures_before_cool_off:
                    cool_off_proxies[proxy] = time.time()

    # Update source reputation based on the success rate
    proxy_sources_reputation[source] = success_count / total_proxies if total_proxies > 0 else 0
    return validated_proxies

# Proxy testing function with failure handling
async def test_proxy(session, proxy):
    test_url = "http://www.google.com"
    try:
        async with limiter:
            async with session.get(test_url, proxy=f"http://{proxy}", timeout=5) as response:
                if response.status == 200:
                    return True, {"proxy": proxy, "is_working": True, "ip": proxy.split(':')[0], "city": "TestCity", "country": "TestCountry"}
    except Exception as e:
        # Log the failure reason
        return False, {"proxy": proxy, "is_working": False, "ip": proxy.split(':')[0], "city": "Unknown", "country": "Unknown", "error": str(e)}
    return False, {"proxy": proxy, "is_working": False, "ip": proxy.split(':')[0], "city": "Unknown", "country": "Unknown"}

# Asynchronous main function to validate proxies
async def main(proxy_list):
    validated_proxies = await validate_proxies(proxy_list, source="Sample Source")
    if validated_proxies:
        st.success("Proxies validated successfully!")
        save_working_proxies(validated_proxies)

# Function to run async task in a separate thread
def run_async_task_in_thread(proxy_list):
    loop = asyncio.new_event_loop()  # Create a new event loop for the task
    asyncio.set_event_loop(loop)  # Set the event loop
    loop.run_until_complete(main(proxy_list))  # Run the asynchronous task
    loop.close()  # Close the loop after execution

# Streamlit Interface
st.subheader("Step 1: Validate Proxies")
if st.button("Validate Proxies"):
    # Example proxy list to validate
    proxy_list = ['123.456.78.90:8080', '234.567.89.00:8080']  # Replace with your actual proxy list
    # Run the async task in a separate thread to avoid blocking Streamlit
    with ThreadPoolExecutor() as executor:
        executor.submit(run_async_task_in_thread, proxy_list)

# Display cool-off info
st.subheader("Proxy Cool-Off Info")
if cool_off_proxies:
    st.info(f"Proxies currently cooling off: {len(cool_off_proxies)}")
