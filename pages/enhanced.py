import streamlit as st
import os
import tempfile
import google.generativeai as genai
import zipfile
import time
import traceback
import re
import unicodedata
from datetime import datetime, timedelta
import pytz
import csv
from menu import menu_with_redirect
from cairosvg import svg2png
from PIL import Image

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

# Function to generate metadata for images using AI model
def generate_metadata(model, img):
    caption = model.generate_content([
        "Analyze the uploaded image and generate a clear, descriptive, and professional one-line title suitable for a microstock image. The title should summarize the main subject, setting, key themes, and concepts, incorporating potential keywords for searches. Ensure it captures all relevant aspects, including actions, objects, emotions, environment, and context.",
        img
    ])
    tags = model.generate_content([
        "Analyze the uploaded image and generate a comprehensive list of 45–50 relevant and specific keywords that encapsulate all aspects of the image, such as actions, objects, emotions, environment, and context. The first five keywords must be the most relevant. Ensure each keyword is a single word, separated by commas, and optimized for searchability and relevance.",
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

# Function to write metadata to CSV
def write_metadata_to_csv(metadata_list, output_path):
    try:
        with open(output_path, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=['Title', 'Tags'])
            writer.writeheader()
            for metadata in metadata_list:
                writer.writerow(metadata)
        st.success(f"Metadata saved to {output_path}")
    except Exception as e:
        st.error(f"An error occurred while writing to CSV: {e}")
        st.error(traceback.format_exc())

# Function to convert SVG to PNG
def convert_svg_to_png(svg_file):
    try:
        temp_png_path = tempfile.mktemp(suffix='.png')
        with open(temp_png_path, 'wb') as output:
            svg2png(file_obj=svg_file, write_to=output)
        return temp_png_path
    except Exception as e:
        st.error(f"An error occurred while converting SVG to PNG: {e}")
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

    # Check if license has already been validated
    license_file = "license.txt"
    if not st.session_state['license_validated']:
        if os.path.exists(license_file):
            with open(license_file, 'r') as file:
                start_date_str = file.read().strip()
                start_date = datetime.fromisoformat(start_date_str)
                st.session_state['license_validated'] = True
        else:
            # License key input
            validation_key = st.text_input('License Key', type='password')

    # Check if validation key is correct
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
        # Check the license file for the start date
        with open(license_file, 'r') as file:
            start_date_str = file.read().strip()
            start_date = datetime.fromisoformat(start_date_str)

        # Calculate the expiration date
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

        # Save API key in session state
        if api_key:
            st.session_state['api_key'] = api_key

        # Upload SVG files
        uploaded_files = st.file_uploader('Upload SVG Images (Only SVG Supported)', accept_multiple_files=True)

        if uploaded_files:
            valid_files = [file for file in uploaded_files if file.type == 'image/svg+xml']
            invalid_files = [file for file in uploaded_files if file not in valid_files]

            if invalid_files:
                st.error("Only SVG files are supported.")

            if valid_files and st.button("Process"):
                with st.spinner("Processing..."):
                    try:
                        # Check and update upload count for the current date
                        if st.session_state['upload_count']['date'] != current_date.date():
                            st.session_state['upload_count'] = {
                                'date': current_date.date(),
                                'count': 0
                            }
                        
                        # Check if remaining uploads are available
                        if st.session_state['upload_count']['count'] + len(valid_files) > 1000000:
                            remaining_uploads = 1000000 - st.session_state['upload_count']['count']
                            st.warning(f"You have exceeded the upload limit. Remaining uploads for today: {remaining_uploads}")
                            return
                        else:
                            st.session_state['upload_count']['count'] += len(valid_files)
                            st.success(f"Uploads successful. Remaining uploads for today: {1000000 - st.session_state['upload_count']['count']}")

                        genai.configure(api_key=api_key)  # Configure AI model with API key
                        model = genai.GenerativeModel('gemini-1.5-flash')

                        # Create a temporary directory to store the uploaded SVG files
                        with tempfile.TemporaryDirectory() as temp_dir:
                            # Save the uploaded files to the temporary directory
                            image_paths = []
                            for file in valid_files:
                                # Convert SVG to PNG
                                temp_png_path = convert_svg_to_png(file)
                                if temp_png_path:
                                    image_paths.append(temp_png_path)

                            # Process each PNG and generate titles and tags using AI
                            metadata_list = []
                            process_placeholder = st.empty()
                            for i, image_path in enumerate(image_paths):
                                process_placeholder.text(f"Processing Generate Titles and Tags {i + 1}/{len(image_paths)}")
                                try:
                                    metadata = generate_metadata(model, image_path)
                                    metadata_list.append(metadata)
                                except Exception as e:
                                    st.error(f"An error occurred while generating metadata for {os.path.basename(image_path)}: {e}")
                                    st.error(traceback.format_exc())
                                    continue

                            # Write metadata to CSV
                            output_csv_path = os.path.join(temp_dir, 'metadata.csv')
                            write_metadata_to_csv(metadata_list, output_csv_path)

                            # Provide download button for the CSV
                            with open(output_csv_path, 'rb') as csv_file:
                                st.download_button(
                                    label="Download Metadata CSV",
                                    data=csv_file,
                                    file_name="metadata.csv",
                                    mime="text/csv"
                                )

                    except Exception as e:
                        st.error(f"An error occurred: {e}")
                        st.error(traceback.format_exc())  # Print detailed error traceback for debugging

if __name__ == '__main__':
    main()
