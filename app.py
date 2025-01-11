import streamlit as st
import requests
from bs4 import BeautifulSoup
import gzip
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import xml.etree.ElementTree as ET

# Function to fetch and parse a webpage
def fetch_and_parse(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove unnecessary tags
        for tag in soup(['head', 'header', 'footer', 'script', 'style', 'meta']):
            tag.decompose()
        return soup
    except requests.RequestException as e:
        st.error(f"Error fetching URL {url}: {e}")
        return None

# Function to extract and combine text from the page
def extract_text_selectively(soup):
    if not soup:
        return ""
    individual_tags = {'p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', 'tr'}
    container_tags = {'div', 'section', 'article', 'main'}
    excluded_tags = {'style', 'script', 'meta', 'body', 'html', '[document]', 'button'}
    
    text_lines = []
    for element in soup.find_all(True, recursive=True):
        if element.name in excluded_tags:
            continue
        if element.name == 'tr':
            row_text = [cell.get_text(separator=' ', strip=True) for cell in element.find_all(['th', 'td']) if cell.get_text(strip=True)]
            if row_text:
                text_lines.append(', '.join(row_text))
        elif element.name in individual_tags:
            inline_text = ' '.join(element.stripped_strings)
            if inline_text:
                text_lines.append(inline_text)
        elif element.name in container_tags:
            direct_text = ' '.join([t.strip() for t in element.find_all(text=True, recursive=False) if t.strip()])
            if direct_text:
                text_lines.append(direct_text)
    
    combined_text = ' '.join(text_lines)
    return combined_text

# Function to calculate compression ratio
def calculate_compression_ratio(text):
    if not text:
        return 0
    original_size = len(text.encode('utf-8'))
    compressed_size = len(gzip.compress(text.encode('utf-8')))
    return original_size / compressed_size

# Function to parse a sitemap and extract URLs
def parse_sitemap(sitemap_url):
    try:
        response = requests.get(sitemap_url)
        response.raise_for_status()
        tree = ET.ElementTree(ET.fromstring(response.content))
        root = tree.getroot()
        urls = [url.text for url in root.findall(".//url/loc")]
        return urls
    except requests.RequestException as e:
        st.error(f"Error fetching sitemap: {e}")
        return []

# Streamlit app
st.title("URL Compression Ratio Calculator")

# Sidebar input options
st.sidebar.header("Input Method")
option = st.sidebar.radio(
    "Choose how to provide the URLs:",
    ("Paste your sitemap URL", "Paste your URLs", "Upload a spreadsheet with URLs")
)

# Based on the chosen option, handle the input
if option == "Paste your sitemap URL":
    sitemap_url = st.sidebar.text_input("Enter Sitemap URL")
    if sitemap_url:
        urls = parse_sitemap(sitemap_url)
        if urls:
            st.sidebar.success(f"Found {len(urls)} URLs in the sitemap.")

elif option == "Paste your URLs":
    urls_input = st.sidebar.text_area("Paste your URLs (one per line)", height=200)
    urls = [url.strip() for url in urls_input.split("\n") if url.strip()]

elif option == "Upload a spreadsheet with URLs":
    uploaded_file = st.sidebar.file_uploader("Upload an Excel file with a column named 'URL'", type=['xlsx'])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            if 'URL' not in df.columns:
                st.error("The uploaded file must contain a column named 'URL'.")
            else:
                urls = df['URL'].dropna().tolist()
                st.sidebar.success(f"Loaded {len(urls)} URLs from the spreadsheet.")
        except Exception as e:
            st.error(f"Error processing the file: {e}")

# Check if URLs are available for processing
if urls:
    compression_ratios = []
    with st.spinner("Processing URLs..."):
        for url in urls:
            st.write(f"Processing: {url}")
            soup = fetch_and_parse(url)
            combined_text = extract_text_selectively(soup)
            compression_ratio = calculate_compression_ratio(combined_text)
            compression_ratios.append(compression_ratio)

    # Display results in a DataFrame
    results_df = pd.DataFrame({
        "URL": urls,
        "Compression Ratio": compression_ratios
    })
    st.success("Processing completed!")
    st.write("Here are the results:")
    st.dataframe(results_df)

    # Allow download of results
    output = BytesIO()
    results_df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    st.download_button(
        label="Download Results as Excel",
        data=output,
        file_name="compression_ratios.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Visualize compression ratios
    st.subheader("Compression Ratios Visualization")
    plt.figure(figsize=(12, 8))
    bars = plt.bar(results_df['URL'], results_df['Compression Ratio'], color='blue', alpha=0.7, label='Compression Ratio')
    for i, bar in enumerate(bars):
        if results_df['Compression Ratio'][i] > 4.0:
            bar.set_color('red')
    plt.axhline(y=4.0, color='orange', linestyle='--', linewidth=2, label='Spam Threshold (4.0)')
    plt.xticks(rotation=90, fontsize=8)
    plt.title("Compression Ratios of URLs", fontsize=16)
    plt.xlabel("URLs", fontsize=12)
    plt.ylabel("Compression Ratio", fontsize=12)
    plt.legend()
    plt.tight_layout()
    st.pyplot(plt)

