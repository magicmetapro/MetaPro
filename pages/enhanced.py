import streamlit as st
import os
import tempfile
from PIL import Image
import google.generativeai as genai
import zipfile
import time
import traceback
import re
import unicodedata
from datetime import datetime
import pytz
from menu import menu_with_redirect
from xml.etree import ElementTree as ET
import csv
import cairosvg  # For SVG to JPG conversion

st.set_option("client.showSidebarNavigation", False)

# Redirect to app.py if not logged in, otherwise show the navigation menu
menu_with_redirect()

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

# Set timezone
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# Initialize session state
if 'license_validated' not in st.session_state:
    st.session_state['license_validated'] = False

if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

# Normalize text
def normalize_text(text, max_length=100):
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\s]', '', normalized).strip()
    return cleaned[:max_length]

# Generate metadata
def generate_metadata(model, content, filename):
    caption = model.generate_content([  
        "Analyze the content and generate a clear, descriptive, and professional one-line title.",
        content
    ])
    tags = model.generate_content([
        "Analyze the content and generate a list of 45–50 specific keywords.",
        content
    ])
    filtered_tags = re.sub(r'[^\w\s,]', '', tags.text)
    keywords = filtered_tags.split(',')[:49]
    trimmed_tags = ','.join(keywords)
    return [filename, caption.text.strip(), trimmed_tags.strip()]

# Save metadata
def save_metadata_to_csv(metadata_rows):
    csv_file_path = os.path.join(tempfile.gettempdir(), 'metadata.csv')
    with open(csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Filename', 'Title', 'Keywords'])  # CSV header
        writer.writerows(metadata_rows)
    return csv_file_path

# Convert SVG to JPG
def svg_to_jpg(svg_path, output_path):
    try:
        cairosvg.svg2png(url=svg_path, write_to=output_path, dpi=300)
        img = Image.open(output_path)
        img = img.convert("RGB")
        img.save(output_path.replace(".png", ".jpg"), "JPEG")
        return output_path.replace(".png", ".jpg")
    except Exception as e:
        st.error(f"SVG to JPG conversion failed: {e}")
        return None

# Main function
def main():
    st.markdown("<h3>Image and Metadata Processing</h3>", unsafe_allow_html=True)
    if not st.session_state['license_validated']:
        key = st.text_input('License Key', type='password')
        if key == "a":
            st.session_state['license_validated'] = True
            st.success("License validated successfully!")
        elif key:
            st.error("Invalid key.")
        return
    
    api_key = st.text_input('Enter your API Key', value=st.session_state['api_key'] or '')
    if api_key:
        st.session_state['api_key'] = api_key

    uploaded_files = st.file_uploader("Upload JPG, PNG, or SVG files", accept_multiple_files=True)
    if uploaded_files and st.button("Process"):
        with st.spinner("Processing..."):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            metadata_rows = []

            for file in uploaded_files:
                file_path = os.path.join(tempfile.gettempdir(), file.name)
                with open(file_path, 'wb') as f:
                    f.write(file.read())

                if file.type == 'image/svg+xml':
                    jpg_path = svg_to_jpg(file_path, file_path.replace(".svg", ".png"))
                    if jpg_path:
                        img = Image.open(jpg_path)
                        content = f"Converted image with dimensions {img.size}"
                        metadata = generate_metadata(model, content, os.path.basename(jpg_path))
                        metadata_rows.append(metadata)
                else:
                    img = Image.open(file_path)
                    content = f"An image with dimensions {img.size}"
                    metadata = generate_metadata(model, content, file.name)
                    metadata_rows.append(metadata)

            csv_path = save_metadata_to_csv(metadata_rows)
            if csv_path:
                with open(csv_path, 'rb') as file:
                    st.download_button("Download Metadata CSV", file, "metadata.csv", "application/csv")

if __name__ == '__main__':
    main()
