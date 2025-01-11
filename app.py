import streamlit as st
import requests
from bs4 import BeautifulSoup
import gzip
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

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

# Streamlit app
st.title("Emmy's Compression Ratio Calculator")

# Option for user to choose input type
option = st.selectbox(
    "Select Input Type:",
    ["Paste Sitemap URL", "Paste URLs", "Upload an Excel file with URLs"]
)

# Define a submit button
submit_button = st.button("Submit")

# Input fields for the different options
if option == "Paste Sitemap URL":
    sitemap_url = st.text_input("Enter Sitemap URL:")
    urls_input_field = False
    file_input_field = False
elif option == "Paste URLs":
    urls_input_field = st.text_area("Paste URLs here (one per line):")
    sitemap_url = None
    file_input_field = False
elif option == "Upload an Excel file with URLs":
    file_input_field = st.file_uploader("Upload your Excel file (must contain a column named 'URL')", type=['xlsx'])
    urls_input_field = False
    sitemap_url = None

# Only proceed if the submit button is pressed
if submit_button:
    compression_ratios = []
    urls = []

    if option == "Paste Sitemap URL" and sitemap_url:
        response = requests.get(sitemap_url)
        if response.status_code == 200:
            sitemap = response.text
            soup = BeautifulSoup(sitemap, 'html.parser')
            urls = [loc.text for loc in soup.find_all('loc')]
            st.write(f"Found {len(urls)} URLs in the Sitemap.")
                
    elif option == "Paste URLs" and urls_input_field:
        urls = urls_input_field.split("\n")
        st.write(f"Found {len(urls)} URLs.")

    elif option == "Upload an Excel file with URLs" and file_input_field:
        # Read the uploaded Excel file
        try:
            df = pd.read_excel(file_input_field)
            if 'URL' not in df.columns:
                st.error("The uploaded file must contain a column named 'URL'.")
            else:
                urls = df['URL'].tolist()
                st.write(f"Found {len(urls)} URLs in the Excel file.")
        except Exception as e:
            st.error(f"Error processing the file: {e}")

    if urls:
        # Process the URLs and calculate compression ratios
        with st.spinner("Processing URLs..."):
            for url in urls:
                soup = fetch_and_parse(url)
                combined_text = extract_text_selectively(soup)
                compression_ratio = calculate_compression_ratio(combined_text)
                compression_ratios.append(compression_ratio)

        # Prepare DataFrame for displaying
        results_df = pd.DataFrame({'URL': urls, 'Compression Ratio': compression_ratios})

        # Count how many URLs have a compression ratio above 4.0
        high_compression_ratio_count = sum(ratio > 4.0 for ratio in compression_ratios)

        # Display the message about pages with compression ratios above 4.0
        st.markdown(f"**Here are Pages with Higher compression ratios: {high_compression_ratio_count}**", unsafe_allow_html=True))
        
        # Allow download of the results as an Excel file
        st.subheader("Download Results")
        output = BytesIO()
        results_df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        st.download_button(
            label="Download Results as Excel",
            data=output,
            file_name="compression_ratios.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
       
        # Scrollable table to display the URLs and compression ratios
        st.subheader("Compression Ratios Table")
        st.dataframe(results_df, height=300)  # Scrollable table

        # Visualize compression ratios
        st.subheader("Compression Ratios Visualization")
        plt.figure(figsize=(12, 8))
        bars = plt.bar(urls, compression_ratios, color='blue', alpha=0.7, label='Compression Ratio')
        for i, bar in enumerate(bars):
            if compression_ratios[i] > 4.0:
                bar.set_color('red')
        plt.axhline(y=4.0, color='orange', linestyle='--', linewidth=2, label='Spam Threshold (4.0)')
        plt.xticks(rotation=90, fontsize=8)
        plt.title("Compression Ratios of URLs", fontsize=16)
        plt.xlabel("URLs", fontsize=12)
        plt.ylabel("Compression Ratio", fontsize=12)
        plt.legend()
        plt.tight_layout()
        st.pyplot(plt)

# Sidebar for app instructions
st.sidebar.title("How to Use This App")
st.sidebar.markdown("""
This tool helps content teams calculate the compression ratio of pages in order assess the quality and relevance of their content. The compression ratio gives insights into the following:

- **Risk of a future algorithmic penalty**
- **Absence of page identity**
- **Potential for ranking instabilities**
- **Redundancy of words, context, semantics, and entity relationships on the page**

### What is a Compression Ratio?
The compression ratio is the degree to which a page can be compressed without losing its identity or meaning. A higher compression ratio suggests that the content on the page is redundant, filled with filler words, and potentially low in quality. In contrast, a lower ratio suggests that the page is rich in content.

### Relevance in Content Marketing & SEO:
Search engines aim to save resources by compressing web content during indexing. Pages with high compression ratios (above 4.0) are considered to be spammy or full of fillers. This can hurt your rankings, cause traffic declines, and increase the risk of algorithmic penalties.

For better content marketing and SEO, focus on creating content that adds value and reduces redundancy, ensuring a low compression ratio.

[Read More Here](https://gofishdigital.com/blog/identify-low-quality-pages-compression-python-seo/)  )
""")
