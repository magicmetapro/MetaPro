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
import csv
import cairosvg
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
    return cleaned[:max_length]  # Truncate to the specified max length

# Function to generate metadata for images or SVG using AI model
def generate_metadata(model, img_path, is_svg=False):
    if is_svg:
        with open(img_path, 'rb') as file:
            content = file.read()
        caption = model.generate_content([
            "Analyze the uploaded SVG file and generate a clear, descriptive, and professional one-line title suitable for a microstock image. The title should summarize the main subject, setting, key themes, and concepts, incorporating potential keywords for searches.",
            content
        ])
        tags = model.generate_content([
            "Analyze the uploaded SVG file and generate a comprehensive list of 45–50 relevant and specific keywords that encapsulate all aspects of the image, such as actions, objects, emotions, environment, and context. Ensure each keyword is a single word, separated by commas, and optimized for searchability and relevance.",
            content
        ])
    else:
        img = Image.open(img_path)
        caption = model.generate_content([
            "Analyze the uploaded image and generate a clear, descriptive, and professional one-line title suitable for a microstock image. The title should summarize the main subject, setting, key themes, and concepts, incorporating potential keywords for searches.",
            img
        ])
        tags = model.generate_content([
            "Analyze the uploaded image and generate a comprehensive list of 45–50 relevant and specific keywords that encapsulate all aspects of the image, such as actions, objects, emotions, environment, and context. Ensure each keyword is a single word, separated by commas, and optimized for searchability and relevance.",
            img
        ])

    # Filter out undesirable characters from the generated tags
    filtered_tags = re.sub(r'[^\w\s,]', '', tags.text)

    # Trim the generated keywords if they exceed 49 words
    keywords = filtered_tags.split(',')[:49]  # Limit to 49 words
    trimmed_tags = ','.join(keywords)

    return {
        'Title': caption.text.strip(),  # Remove leading/trailing whitespace
        'Tags': trimmed_tags.strip()
    }

# Function to process SVG files and convert to PNG for preview
def process_svg(svg_path):
    try:
        # Convert SVG to PNG
        temp_dir = tempfile.gettempdir()
        png_path = os.path.join(temp_dir, f"{os.path.basename(svg_path)}.png")
        cairosvg.svg2png(url=svg_path, write_to=png_path)
        return png_path
    except Exception as e:
        raise Exception(f"Error converting SVG to PNG: {e}")

# Function to save metadata to CSV
def save_metadata_to_csv(metadata_list, output_path):
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['Filename', 'Title', 'Keywords', 'Category', 'Releases'])  # CSV headers
        for metadata in metadata_list:
            csvwriter.writerow([
                metadata.get('Filename', ''),
                metadata.get('Title', ''),
                metadata.get('Tags', ''),
                '',  # Category placeholder
                ''   # Releases placeholder
            ])

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

    # License validation (unchanged)
    license_file = "license.txt"
    if not st.session_state['license_validated']:
        if os.path.exists(license_file):
            with open(license_file, 'r') as file:
                start_date_str = file.read().strip()
                start_date = datetime.fromisoformat(start_date_str)
                st.session_state['license_validated'] = True
        else:
            validation_key = st.text_input('License Key', type='password')

    correct_key = "a"
    if not st.session_state['license_validated'] and validation_key:
        if validation_key == correct_key:
            st.session_state['license_validated'] = True
            start_date = datetime.now(JAKARTA_TZ)
            with open(license_file, 'w') as file:
                file.write(start_date.isoformat())
        else:
            st.error("Invalid validation key. Please enter the correct key.")

    if st.session_state['license_validated']:
        with open(license_file, 'r') as file:
            start_date_str = file.read().strip()
            start_date = datetime.fromisoformat(start_date_str)

        expiration_date = start_date + timedelta(days=91)
        current_date = datetime.now(JAKARTA_TZ)

        if current_date > expiration_date:
            st.error("Your license has expired. Please contact support for a new license key.")
            return
        else:
            days_remaining = (expiration_date - current_date).days
            st.success(f"License valid. You have {days_remaining} days remaining. Max 45 files per upload, unlimited daily uploads.")

        # API Key input
        api_key = st.text_input('Enter your [API](https://makersuite.google.com/app/apikey) Key', value=st.session_state['api_key'] or '')
        if api_key:
            st.session_state['api_key'] = api_key

        # Upload image and SVG files
        uploaded_files = st.file_uploader('Upload Images or SVG (Only JPG, PNG, SVG Supported)', accept_multiple_files=True)

        if uploaded_files:
            valid_files = [file for file in uploaded_files if file.type in ['image/jpeg', 'image/png', 'image/jpg', 'image/svg+xml']]
            invalid_files = [file for file in uploaded_files if file not in valid_files]

            if invalid_files:
                st.error("Only JPG, PNG, and SVG files are supported.")

            if valid_files and st.button("Process"):
                with st.spinner("Processing..."):
                    try:
                        if st.session_state['upload_count']['date'] != current_date.date():
                            st.session_state['upload_count'] = {
                                'date': current_date.date(),
                                'count': 0
                            }

                        if st.session_state['upload_count']['count'] + len(valid_files) > 1000000:
                            remaining_uploads = 1000000 - st.session_state['upload_count']['count']
                            st.warning(f"You have exceeded the upload limit. Remaining uploads for today: {remaining_uploads}")
                            return
                        else:
                            st.session_state['upload_count']['count'] += len(valid_files)
                            st.success(f"Uploads successful. Remaining uploads for today: {1000000 - st.session_state['upload_count']['count']}")

                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')

                        with tempfile.TemporaryDirectory() as temp_dir:
                            image_paths = []
                            metadata_list = []

                            for file in valid_files:
                                temp_file_path = os.path.join(temp_dir, file.name)
                                with open(temp_file_path, 'wb') as f:
                                    f.write(file.read())

                                is_svg = file.type == 'image/svg+xml'

                                if is_svg:
                                    png_preview_path = process_svg(temp_file_path)
                                    metadata = generate_metadata(model, temp_file_path, is_svg=True)
                                else:
                                    jpeg_image_path = convert_to_jpeg(temp_file_path)
                                    metadata = generate_metadata(model, jpeg_image_path)

                                metadata['Filename'] = file.name
                                metadata_list.append(metadata)

                            # Save metadata to CSV
                            csv_output_path = os.path.join(temp_dir, 'metadata.csv')
                            save_metadata_to_csv(metadata_list, csv_output_path)

                            st.success("Processing complete. Download your metadata below:")
                            with open(csv_output_path, 'rb') as csv_file:
                                st.download_button(
                                    label="Download Metadata CSV",
                                    data=csv_file,
                                    file_name="metadata.csv",
                                    mime="text/csv"
                                )

                    except Exception as e:
                        st.error(f"An error occurred: {e}")
                        st.error(traceback.format_exc())

if __name__ == '__main__':
    main()
