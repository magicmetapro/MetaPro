import streamlit as st
import os
import tempfile
from PIL import Image
import cairosvg
import google.generativeai as genai
import iptcinfo3
import zipfile
import time
import traceback
import re
import csv
import unicodedata
import pandas as pd
from datetime import datetime, timedelta
import pytz
from menu import menu_with_redirect

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

# Set the timezone to UTC+7 Jakarta
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# Initialize session state for license validation
if 'license_validated' not in st.session_state:
    st.session_state['license_validated'] = False

if 'upload_count' not in st.session_state:
    st.session_state['upload_count'] = {
        'date': None,
        'count': 0
    }

if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

# Function to normalize text
def normalize_text(text, max_length=100):
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\s]', '', normalized).strip()
    return cleaned[:max_length]

# Function to process SVG files and convert to PNG
def convert_svg_to_png(svg_path):
    try:
        png_path = svg_path.rsplit('.', 1)[0] + '.png'
        cairosvg.svg2png(url=svg_path, write_to=png_path)
        return png_path
    except Exception as e:
        raise Exception(f"Error converting SVG to PNG: {e}")

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

    # Creating metadata row
    metadata_row = [
        filename,
        caption.text.strip(),
        trimmed_tags.strip(),
        3,  # Dummy category, you can adjust this as per your needs
        'Haleeq Whitten, Ludovic Hillion, Morgan Greentstreet, Christine Manore'  # Example release names
    ]

    return metadata_row

# Function to save metadata to a CSV file
def save_metadata_to_csv(metadata_rows):
    csv_file_path = os.path.join(tempfile.gettempdir(), 'metadata.csv')
    try:
        with open(csv_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Filename', 'Title', 'Keywords', 'Category', 'Release Names'])  # CSV header
            writer.writerows(metadata_rows)  # Write metadata rows

        return csv_file_path
    except Exception as e:
        st.error(f"An error occurred while saving CSV: {e}")
        st.error(traceback.format_exc())
        return None

# Main function
def main():
    """Main function for the Streamlit app."""

    # Display WhatsApp chat link
    st.markdown("""
    <div style="text-align: center; margin-top: 20px;">
        <a href="https://wa.me/6282265298845" target="_blank">
            <button style="background-color: #1976d2; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
                MetaPro
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)

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
                            content = extract_svg_content(temp_path)
                        else:
                            img = Image.open(temp_path)
                            content = f"An image with dimensions {img.size}"

                        # Generate metadata
                        metadata_row = generate_metadata(model, content, file.name)
                        metadata_rows.append(metadata_row)

                    # Save metadata to CSV
                    csv_path = save_metadata_to_csv(metadata_rows)
                    if csv_path:
                        with open(csv_path, 'rb') as csv_file:
                            st.download_button("Download Metadata CSV", csv_file, "metadata.csv", "application/csv")

                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    st.error(traceback.format_exc())

if __name__ == '__main__':
    main()
