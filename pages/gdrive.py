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
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
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

if 'uploaded_file_id' not in st.session_state:
    st.session_state['uploaded_file_id'] = None

# Function to normalize and clean text
def normalize_text(text):
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    return normalized

# Function to generate metadata for images using AI model
def generate_metadata(model, img):
    caption = model.generate_content(["Create a descriptive title in English up to 12 words long, highlighting the main elements of the image. Identify primary subjects, objects, activities, and context. Include relevant SEO keywords to ensure the title is engaging and informative. Avoid mentioning human names, brand names, product names, or company names.", img])
    tags = model.generate_content(["Create up to 45 keywords in English that are relevant to the image (each keyword must be one word, separated by commas). Ensure each keyword is a single word, separated by commas.", img])

    # Filter out undesirable characters from the generated tags
    filtered_tags = re.sub(r'[^\w\s,]', '', tags.text)
    
    # Trim the generated keywords if they exceed 49 words
    keywords = filtered_tags.split(',')[:49]  # Limit to 49 words
    trimmed_tags = ','.join(keywords)
    
    return {
        'Title': caption.text.strip(),  # Remove leading/trailing whitespace
        'Tags': trimmed_tags.strip()
    }

# Function to embed metadata into images
def embed_metadata(image_path, metadata, progress_bar, files_processed, total_files):
    try:
        # Simulate delay
        time.sleep(1)

        # Open the image file
        img = Image.open(image_path)

        # Load existing IPTC data (if any)
        iptc_data = iptcinfo3.IPTCInfo(image_path, force=True)

        # Clear existing IPTC metadata
        for tag in iptc_data._data:
            iptc_data._data[tag] = []

        # Update IPTC data with new metadata
        iptc_data['keywords'] = [metadata.get('Tags', '')]  # Keywords
        iptc_data['caption/abstract'] = [metadata.get('Title', '')]  # Title

        # Save the image with the embedded metadata
        iptc_data.save()

        # Update progress bar
        files_processed += 1
        progress_bar.progress(files_processed / total_files)
        progress_bar.text(f"Embedding metadata for image {files_processed}/{total_files}")

        # Return the updated image path for further processing
        return image_path

    except Exception as e:
        st.error(f"An error occurred while embedding metadata: {e}")
        st.error(traceback.format_exc())  # Print detailed error traceback for debugging

def zip_processed_images(image_paths):
    try:
        zip_file_path = os.path.join(tempfile.gettempdir(), 'processed_images.zip')

        with zipfile.ZipFile(zip_file_path, 'w') as zipf:
            for image_path in image_paths:
                zipf.write(image_path, arcname=os.path.basename(image_path))

        return zip_file_path

    except Exception as e:
        st.error(f"An error occurred while zipping images: {e}")
        st.error(traceback.format_exc())
        return None

def upload_to_drive(zip_file_path, credentials):
    try:
        service = build('drive', 'v3', credentials=credentials)
        file_metadata = {
            'name': os.path.basename(zip_file_path),
            'mimeType': 'application/zip'
        }
        media = MediaFileUpload(zip_file_path, mimetype='application/zip', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id,webViewLink').execute()

        # Make the file publicly accessible
        service.permissions().create(
            fileId=file['id'],
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        st.session_state['uploaded_file_id'] = file.get('id')
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"An error occurred while uploading to Google Drive: {e}")
        st.error(traceback.format_exc())
        return None

def delete_from_drive(file_id, credentials):
    try:
        service = build('drive', 'v3', credentials=credentials)
        service.files().delete(fileId=file_id).execute()
        st.success("File deleted from Google Drive successfully!")
    except Exception as e:
        st.error(f"An error occurred while deleting the file from Google Drive: {e}")
        st.error(traceback.format_exc())

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

        # Upload image files
        uploaded_files = st.file_uploader('Upload Images (Only JPG and JPEG Supported)', accept_multiple_files=True)

        if uploaded_files:
            valid_files = [file for file in uploaded_files if file.type in ['image/jpeg', 'image/jpg']]
            invalid_files = [file for file in uploaded_files if file not in valid_files]

            if invalid_files:
                st.error("Only JPG and JPEG files are supported.")

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
                        model = genai.GenerativeModel('gemini-pro-vision')

                        # Create a temporary directory to store the uploaded images
                        with tempfile.TemporaryDirectory() as temp_dir:
                            # Save the uploaded images to the temporary directory
                            image_paths = []
                            for file in valid_files:
                                temp_image_path = os.path.join(temp_dir, file.name)
                                with open(temp_image_path, 'wb') as f:
                                    f.write(file.read())
                                image_paths.append(temp_image_path)

                            # Process each image and generate titles and tags using AI
                            metadata_list = []
                            process_placeholder = st.empty()
                            for i, image_path in enumerate(image_paths):
                                process_placeholder.text(f"Processing Generate Titles and Tags {i + 1}/{len(image_paths)}")
                                try:
                                    img = Image.open(image_path)
                                    metadata = generate_metadata(model, img)
                                    metadata_list.append(metadata)
                                except Exception as e:
                                    st.error(f"An error occurred while generating metadata for {os.path.basename(image_path)}: {e}")
                                    st.error(traceback.format_exc())
                                    continue

                            # Embed metadata into images
                            total_files = len(image_paths)
                            files_processed = 0

                            # Display the progress bar and current file number
                            progress_placeholder = st.empty()
                            progress_bar = progress_placeholder.progress(0)
                            progress_placeholder.text(f"Processing images 0/{total_files}")

                            processed_image_paths = []
                            for i, (image_path, metadata) in enumerate(zip(image_paths, metadata_list)):
                                process_placeholder.text(f"Embedding metadata for image {i + 1}/{len(image_paths)}")
                                updated_image_path = embed_metadata(image_path, metadata, progress_bar, files_processed, total_files)
                                if updated_image_path:
                                    processed_image_paths.append(updated_image_path)
                                    files_processed += 1
                                    # Update progress bar and current file number
                                    progress_bar.progress(files_processed / total_files)

                            # Zip processed images
                            zip_file_path = zip_processed_images(processed_image_paths)

                            if zip_file_path:
                               # st.success(f"Successfully zipped processed {zip_file_path}")

                                # Upload zip file to Google Drive and get the shareable link
                                credentials = service_account.Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/drive.file'])
                                drive_link = upload_to_drive(zip_file_path, credentials)

                                if drive_link:
                                    st.success("File uploaded to Google Drive successfully!")
                                    st.markdown(f"[Download processed images from Google Drive]({drive_link})")

                    except Exception as e:
                        st.error(f"An error occurred: {e}")
                        st.error(traceback.format_exc())  # Print detailed error traceback for debugging

    if st.session_state['uploaded_file_id']:
        if st.button("Delete Uploaded File from Google Drive"):
            with st.spinner("Deleting file..."):
                try:
                    credentials = service_account.Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/drive.file'])
                    delete_from_drive(st.session_state['uploaded_file_id'], credentials)
                    st.session_state['uploaded_file_id'] = None
                except Exception as e:
                    st.error(f"An error occurred while deleting the file: {e}")

if __name__ == '__main__':
    main()
