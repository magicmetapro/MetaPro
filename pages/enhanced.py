import streamlit as st
import os
import tempfile
from PIL import Image
import cairosvg
import google.generativeai as genai
import re
import unicodedata
from datetime import datetime
import pytz
from xml.etree import ElementTree as ET
import csv

st.set_option("client.showSidebarNavigation", False)

# Apply custom styling
st.markdown("""
    <style>
        #MainMenu, header, footer {
            visibility: hidden;
        }
        section[data-testid="stSidebar"] {
            top: 0;
            height: 10vh;
        }
    </style>
    """, unsafe_allow_html=True)

# Set the timezone to UTC+7 Jakarta
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

if 'license_validated' not in st.session_state:
    st.session_state['license_validated'] = False

if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

# Function to normalize text
def normalize_text(text, max_length=100):
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\s]', '', normalized).strip()
    return cleaned[:max_length]  # Truncate to the specified max length

# Function to extract content from SVG files
def extract_svg_content(svg_path):
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        text_elements = [elem.text for elem in root.iter() if elem.text]
        return ' '.join(text_elements)
    except Exception as e:
        st.error(f"Failed to process SVG content: {e}")
        return None

# Function to convert SVG to PNG
def convert_svg_to_png(svg_path, output_path):
    try:
        cairosvg.svg2png(url=svg_path, write_to=output_path)
        return output_path
    except Exception as e:
        st.error(f"Failed to convert SVG to PNG: {e}")
        return None

# Function to generate metadata for images or SVGs using AI model
def generate_metadata(model, content, filename):
    caption = model.generate_content([  
        "Analyze the content and generate a clear, descriptive, and professional one-line title suitable for a microstock image or illustration.",
        content
    ])
    tags = model.generate_content([ 
        "Analyze the content and generate a comprehensive list of 45–50 relevant and specific keywords encapsulating all aspects of the content.",
        content
    ])

    # Filter out undesirable characters from the generated tags
    filtered_tags = re.sub(r'[^\w\s,]', '', tags.text)
    keywords = filtered_tags.split(',')[:49]  # Limit to 49 words
    trimmed_tags = ','.join(keywords)

    return [
        filename,
        caption.text.strip(),
        trimmed_tags.strip(),
        "",  # Placeholder for Category
        ""  # Placeholder for Releases
    ]

# Function to save metadata to a CSV file
def save_metadata_to_csv(metadata_rows):
    csv_file_path = os.path.join(tempfile.gettempdir(), 'metadata.csv')
    try:
        with open(csv_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Filename', 'Title', 'Keywords', 'Category', 'Releases'])  # CSV header
            writer.writerows(metadata_rows)  # Write metadata rows

        return csv_file_path
    except Exception as e:
        st.error(f"An error occurred while saving CSV: {e}")
        return None

def main():
    st.title("SVG to PNG Metadata Generator")

    if not st.session_state['license_validated']:
        validation_key = st.text_input('License Key', type='password')
        correct_key = "a"

        if validation_key and validation_key == correct_key:
            st.session_state['license_validated'] = True
            st.success("License validated successfully!")
        elif validation_key:
            st.error("Invalid validation key. Please try again.")
        return

    api_key = st.text_input('Enter your [API](https://makersuite.google.com/app/apikey) Key', value=st.session_state.get('api_key', ''))

    if api_key:
        st.session_state['api_key'] = api_key

    uploaded_files = st.file_uploader('Upload Images or SVGs', accept_multiple_files=True)

    if uploaded_files:
        valid_files = [file for file in uploaded_files if file.type in ['image/jpeg', 'image/png', 'image/jpg', 'image/svg+xml']]
        if not valid_files:
            st.error("Only JPG, PNG, and SVG files are supported.")
            return

        if st.button("Process"):
            with st.spinner("Processing..."):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')

                    metadata_rows = []
                    for file in valid_files:
                        temp_path = os.path.join(tempfile.gettempdir(), file.name)
                        with open(temp_path, 'wb') as f:
                            f.write(file.read())

                        if file.type == 'image/svg+xml':
                            png_path = temp_path.replace('.svg', '.png')
                            convert_svg_to_png(temp_path, png_path)
                            content = extract_svg_content(temp_path)
                            metadata_rows.append(generate_metadata(model, content, os.path.basename(png_path)))

                    # Save metadata to CSV
                    csv_path = save_metadata_to_csv(metadata_rows)
                    if csv_path:
                        with open(csv_path, 'rb') as csv_file:
                            st.download_button("Download Metadata CSV", csv_file, "metadata.csv", "application/csv")

                except Exception as e:
                    st.error(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
