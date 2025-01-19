import streamlit as st
import os
import tempfile
from PIL import Image
import google.generativeai as genai
import iptcinfo3
import zipfile
import time
import traceback
import re
import unicodedata
from datetime import datetime, timedelta
import pytz
from menu import menu_with_redirect
from xml.etree import ElementTree as ET

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

# Function to generate metadata for images or SVGs using AI model
def generate_metadata(model, content):
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

    return {
        'Title': caption.text.strip(),
        'Tags': trimmed_tags.strip()
    }

# Function to zip processed files
def zip_processed_files(file_paths):
    try:
        zip_file_path = os.path.join(tempfile.gettempdir(), 'processed_files.zip')

        with zipfile.ZipFile(zip_file_path, 'w') as zipf:
            for file_path in file_paths:
                zipf.write(file_path, arcname=os.path.basename(file_path))

        return zip_file_path

    except Exception as e:
        st.error(f"An error occurred while zipping files: {e}")
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

uploaded_files = st.file_uploader(
    'Upload Images or SVGs (Only JPG, PNG, and SVG Supported)', 
    accept_multiple_files=True
)

if uploaded_files:
    # Define valid MIME types
    valid_mime_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/svg+xml']

    # Filter valid files based on MIME type
    valid_files = [file for file in uploaded_files if file.type in valid_mime_types]
    invalid_files = [file for file in uploaded_files if file.type not in valid_mime_types]

    if invalid_files:
        st.error("Only JPG, PNG, and SVG files are supported.")

    if valid_files:
        st.success(f"Successfully uploaded {len(valid_files)} valid file(s).")


        if st.button("Process"):
            with st.spinner("Processing..."):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')

                    processed_files = []
                    for file in valid_files:
                        temp_path = os.path.join(tempfile.gettempdir(), file.name)
                        with open(temp_path, 'wb') as f:
                            f.write(file.read())

                        if file.type == 'image/svg+xml':
                            content = extract_svg_content(temp_path)
                        else:
                            img = Image.open(temp_path)
                            content = f"An image with dimensions {img.size}"

                        metadata = generate_metadata(model, content)
                        normalized_title = normalize_text(metadata['Title'])
                        new_file_path = os.path.join(tempfile.gettempdir(), f"{normalized_title}.txt")
                        
                        with open(new_file_path, 'w') as meta_file:
                            meta_file.write(f"Title: {metadata['Title']}\n")
                            meta_file.write(f"Keywords: {metadata['Tags']}\n")

                        processed_files.append(new_file_path)

                    zip_path = zip_processed_files(processed_files)
                    if zip_path:
                        with open(zip_path, 'rb') as zip_file:
                            st.download_button("Download Processed Files", zip_file, "processed_files.zip", "application/zip")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    st.error(traceback.format_exc())

if __name__ == '__main__':
    main()
