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
st.title("URL Compression Ratio Calculator")

# Option for user to choose input type
option = st.selectbox(
    "Select Input Type:",
    ["Paste Sitemap URL", "Paste URLs", "Upload an Excel file with URLs"]
)

if option == "Paste Sitemap URL":
    sitemap_url = st.text_input("Enter Sitemap URL:")
    if sitemap_url:
        response = requests.get(sitemap_url)
        if response.status_code == 200:
            sitemap = response.text
            soup = BeautifulSoup(sitemap, 'html.parser')
            urls = [loc.text for loc in soup.find_all('loc')]
            st.write(f"Found {len(urls)} URLs in the Sitemap.")
            
            # Process the URLs and calculate compression ratios
            compression_ratios = []
            with st.spinner("Processing URLs..."):
                for url in urls:
                    soup = fetch_and_parse(url)
                    combined_text = extract_text_selectively(soup)
                    compression_ratio = calculate_compression_ratio(combined_text)
                    compression_ratios.append(compression_ratio)

            # Find the number of URLs with compression ratios above 4.0
            high_compression_count = sum(1 for ratio in compression_ratios if ratio > 4.0)

            # Display the bolded message in red
            st.markdown(f"**<span style='color:red'>Number of pages with compression ratios above 4.0: {high_compression_count}</span>**", unsafe_allow_html=True)

            # Create a DataFrame for the URLs and compression ratios
            df = pd.DataFrame({
                'URL': urls,
                'Compression Ratio': compression_ratios
            })

            # Display the scrollable table
            st.subheader("URLs and Compression Ratios")
            st.dataframe(df, use_container_width=True)

            # Visualize compression ratios
            st.subheader("Compression Ratios Visualization")
            try:
                plt.figure(figsize=(12, 8))
                bars = plt.bar(df['URL'], df['Compression Ratio'], color='blue', alpha=0.7, label='Compression Ratio')
                for i, bar in enumerate(bars):
                    if df['Compression Ratio'][i] > 4.0:
                        bar.set_color('red')
                plt.axhline(y=4.0, color='orange', linestyle='--', linewidth=2, label='Spam Threshold (4.0)')
                plt.xticks(rotation=90, fontsize=8)
                plt.title("Compression Ratios of URLs", fontsize=16)
                plt.xlabel("URLs", fontsize=12)
                plt.ylabel("Compression Ratio", fontsize=12)
                plt.legend()
                plt.tight_layout()
                st.pyplot(plt)
            except Exception as e:
                st.error(f"Error generating the plot: {e}")

            # Create an Excel file for download
            output = BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            output.seek(0)

            # Provide the download button for the Excel file
            st.download_button(
                label="Download Compression Ratios as Excel",
                data=output,
                file_name="compression_ratios.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

elif option == "Paste URLs":
    urls_input = st.text_area("Paste URLs here (one per line):")
    if urls_input:
        urls = urls_input.split("\n")
        st.write(f"Found {len(urls)} URLs.")
        
        # Process the URLs and calculate compression ratios
        compression_ratios = []
        with st.spinner("Processing URLs..."):
            for url in urls:
                soup = fetch_and_parse(url)
                combined_text = extract_text_selectively(soup)
                compression_ratio = calculate_compression_ratio(combined_text)
                compression_ratios.append(compression_ratio)

        # Find the number of URLs with compression ratios above 4.0
        high_compression_count = sum(1 for ratio in compression_ratios if ratio > 4.0)

        # Display the bolded message in red
        st.markdown(f"**<span style='color:red'>Number of pages with compression ratios above 4.0: {high_compression_count}</span>**", unsafe_allow_html=True)

        # Create a DataFrame for the URLs and compression ratios
        df = pd.DataFrame({
            'URL': urls,
            'Compression Ratio': compression_ratios
        })

        # Display the scrollable table
        st.subheader("URLs and Compression Ratios")
        st.dataframe(df, use_container_width=True)

        # Visualize compression ratios
        st.subheader("Compression Ratios Visualization")
        try:
            plt.figure(figsize=(12, 8))
            bars = plt.bar(df['URL'], df['Compression Ratio'], color='blue', alpha=0.7, label='Compression Ratio')
            for i, bar in enumerate(bars):
                if df['Compression Ratio'][i] > 4.0:
                    bar.set_color('red')
            plt.axhline(y=4.0, color='orange', linestyle='--', linewidth=2, label='Spam Threshold (4.0)')
            plt.xticks(rotation=90, fontsize=8)
            plt.title("Compression Ratios of URLs", fontsize=16)
            plt.xlabel("URLs", fontsize=12)
            plt.ylabel("Compression Ratio", fontsize=12)
            plt.legend()
            plt.tight_layout()
            st.pyplot(plt)
        except Exception as e:
            st.error(f"Error generating the plot: {e}")

        # Create an Excel file for download
        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)

        # Provide the download button for the Excel file
        st.download_button(
            label="Download Compression Ratios as Excel",
            data=output,
            file_name="compression_ratios.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

elif option == "Upload an Excel file with URLs":
    uploaded_file = st.file_uploader("Upload your Excel file (must contain a column named 'URL')", type=['xlsx'])
    if uploaded_file:
        # Read the uploaded Excel file
        try:
            df = pd.read_excel(uploaded_file)
            if 'URL' not in df.columns:
                st.error("The uploaded file must contain a column named 'URL'.")
            else:
                compression_ratios = []
                with st.spinner("Processing URLs..."):
                    for index, row in df.iterrows():
                        url = row['URL']
                        soup = fetch_and_parse(url)
                        combined_text = extract_text_selectively(soup)
                        compression_ratio = calculate_compression_ratio(combined_text)
                        compression_ratios.append(compression_ratio)
                
                # Add compression ratios to DataFrame
                df['Compression Ratio'] = compression_ratios

                st.success("Processing completed!")
                st.write("Here are the results:")
                st.dataframe(df)

                # Find the number of URLs with compression ratios above 4.0
                high_compression_count = sum(1 for ratio in compression_ratios if ratio > 4.0)

                # Display the bolded message in red
                st.markdown(f"**<span style='color:red'>Number of pages with compression ratios above 4.0: {high_compression_count}</span>**", unsafe_allow_html=True)

                # Allow download of results
                output = BytesIO()
                df.to_excel(output, index=False, engine='openpyxl')
                output.seek(0)
                st.download_button(
                    label="Download Results as Excel",
                    data=output,
                    file_name="compression_ratios.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

