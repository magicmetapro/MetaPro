import streamlit as st
import os
import tempfile
import xml.etree.ElementTree as ET
import csv
import time
from datetime import datetime, timedelta
import pytz
import unicodedata
import re
from io import StringIO

# Set the timezone to UTC+7 Jakarta
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# Function to normalize text
def normalize_text(text, max_length=100):
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\s]', '', normalized).strip()
    return cleaned[:max_length]  # Truncate to the specified max length

# Function to extract metadata from SVG
def extract_metadata_from_svg(svg_file):
    try:
        tree = ET.parse(svg_file)
        root = tree.getroot()

        # Default namespace for SVG metadata
        metadata = {}

        # Find the <metadata> tag and extract title and keywords
        metadata_tag = root.find('.//{http://www.w3.org/2000/svg}metadata')
        if metadata_tag is not None:
            title = metadata_tag.find('.//{http://purl.org/dc/elements/1.1/}title')
            keywords = metadata_tag.find('.//{http://purl.org/dc/elements/1.1/}subject')

            metadata['Title'] = title.text if title is not None else 'No title'
            metadata['Keywords'] = keywords.text if keywords is not None else 'No keywords'

        return metadata
    except Exception as e:
        st.error(f"Error extracting metadata from SVG: {e}")
        return None

# Function to write metadata to CSV
def write_metadata_to_csv(metadata_list, output_csv):
    try:
        # Write metadata to CSV file
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Title', 'Keywords']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for metadata in metadata_list:
                writer.writerow(metadata)
    except Exception as e:
        st.error(f"Error writing metadata to CSV: {e}")

# Main function
def main():
    st.title("SVG Metadata Extractor and Exporter")

    # Upload SVG files
    uploaded_files = st.file_uploader("Upload SVG files", accept_multiple_files=True, type=['svg'])

    if uploaded_files:
        # Process SVG files
        metadata_list = []
        with st.spinner("Processing SVG files..."):
            for uploaded_file in uploaded_files:
                st.write(f"Processing {uploaded_file.name}...")
                metadata = extract_metadata_from_svg(uploaded_file)
                if metadata:
                    metadata_list.append(metadata)

        # Check if metadata was extracted
        if metadata_list:
            # Create a CSV export
            output_csv = os.path.join(tempfile.gettempdir(), "metadata_output.csv")
            write_metadata_to_csv(metadata_list, output_csv)

            # Provide the CSV file for download
            with open(output_csv, 'rb') as csvfile:
                st.download_button(
                    label="Download Metadata CSV",
                    data=csvfile,
                    file_name="metadata_output.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main()
