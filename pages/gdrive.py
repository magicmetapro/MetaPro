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
from googleapiclient.errors import HttpError
from menu import menu_with_redirect
import dropbox

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

if 'credentials_json' not in st.session_state:
    st.session_state['credentials_json'] = None

if 'uploaded_files' not in st.session_state:
    st.session_state['uploaded_files'] = []

if 'dropbox_token' not in st.session_state:
    st.session_state['dropbox_token'] = None

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
        # Open the image file
        img = Image.open(image_path)

        # Ensure the image is in JPEG format
        if img.format != 'JPEG':
            img = img.convert('RGB')
            image_path = image_path.replace('.png', '.jpg').replace('.jpeg', '.jpg')
            img.save(image_path, format='JPEG')

        # Load existing IPTC data (if any)
        iptc_data = iptcinfo3.IPTCInfo(image_path, force=True)

        # Update IPTC data with new metadata
        iptc_data['keywords'] = [metadata.get('Tags', '')]  # Keywords
        iptc_data['caption/abstract'] = [metadata.get('Title', '')]  # Title

        # Save the image with the embedded metadata
        iptc_data.save_as(image_path)

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

        return file.get('id'), file.get('webViewLink')
    except Exception as e:
        st.error(f"An error occurred while uploading to Google Drive: {e}")
        st.error(traceback.format_exc())
        return None, None

def delete_file_from_drive(file_id, credentials):
    try:
        service = build('drive', 'v3', credentials=credentials)
        service.files().delete(fileId=file_id).execute()
        st.success("File deleted successfully from Google Drive.")
    except HttpError as error:
        st.error(f"An error occurred while deleting the file: {error}")
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.error(traceback.format_exc())

def upload_to_dropbox(zip_file_path, dropbox_token):
    try:
        dbx = dropbox.Dropbox(dropbox_token)
        with open(zip_file_path, 'rb') as f:
            dbx.files_upload(f.read(), '/' + os.path.basename(zip_file_path), mute=True)
        shared_link_metadata = dbx.sharing_create_shared_link_with_settings('/' + os.path.basename(zip_file_path))
        return shared_link_metadata.url
    except dropbox.exceptions.ApiError as e:
        st.error(f"An error occurred while uploading to Dropbox: {e}")
        st.error(traceback.format_exc())
        return None

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
    correct_key = "dian12345"

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
            st.success(f"License valid. You have {days_remaining} days remaining. Max 100 images per day.")

        # Google API Key input
        api_key = st.text_input('Google API Key', type='password')
        if api_key:
            st.session_state['api_key'] = api_key
            genai.configure(api_key=api_key)
            st.success("Google API Key validated successfully.")

        # Dropbox API Key input
        dropbox_token = st.text_input('Dropbox API Key', type='password')
        if dropbox_token:
            st.session_state['dropbox_token'] = dropbox_token
            st.success("Dropbox API Key validated successfully.")

        # File uploader
        uploaded_files = st.file_uploader("Upload Images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

        # Display the upload count and date
        st.write(f"Uploaded {st.session_state['upload_count']['count']} images on {st.session_state['upload_count']['date']}.")

        # Select upload destination
        upload_destination = st.selectbox("Select upload destination", ["Google Drive", "Dropbox"])

        # Process and upload images
        if uploaded_files and api_key:
            current_date_str = current_date.strftime('%Y-%m-%d')

            if st.session_state['upload_count']['date'] != current_date_str:
                st.session_state['upload_count'] = {
                    'date': current_date_str,
                    'count': 0
                }

            total_files = len(uploaded_files)
            if st.session_state['upload_count']['count'] + total_files > 100:
                st.error("Upload limit exceeded. You can upload up to 100 images per day.")
            else:
                progress_bar = st.progress(0)
                files_processed = 0

                try:
                    temp_dir = tempfile.mkdtemp()

                    # Process and save images with metadata
                    processed_image_paths = []
                    for uploaded_file in uploaded_files:
                        temp_image_path = os.path.join(temp_dir, uploaded_file.name)
                        with open(temp_image_path, "wb") as f:
                            f.write(uploaded_file.read())

                        metadata = generate_metadata(genai, temp_image_path)
                        updated_image_path = embed_metadata(temp_image_path, metadata, progress_bar, files_processed, total_files)
                        processed_image_paths.append(updated_image_path)
                        files_processed += 1

                    # Zip the processed images
                    zip_file_path = zip_processed_images(processed_image_paths)

                    # Upload to the selected destination
                    if upload_destination == "Google Drive":
                        credentials_json = st.text_area('Google Drive Service Account Credentials', height=200)
                        if credentials_json:
                            credentials = service_account.Credentials.from_service_account_info(json.loads(credentials_json), scopes=["https://www.googleapis.com/auth/drive.file"])
                            file_id, webview_link = upload_to_drive(zip_file_path, credentials)
                            if file_id and webview_link:
                                st.session_state['uploaded_files'].append({
                                    'file_id': file_id,
                                    'webview_link': webview_link
                                })
                                st.success(f"Upload to Google Drive successful. [View File]({webview_link})")
                                st.session_state['upload_count']['count'] += total_files
                    elif upload_destination == "Dropbox" and dropbox_token:
                        shared_link = upload_to_dropbox(zip_file_path, dropbox_token)
                        if shared_link:
                            st.success(f"Upload to Dropbox successful. [View File]({shared_link})")
                            st.session_state['upload_count']['count'] += total_files

                except Exception as e:
                    st.error(f"An error occurred during processing: {e}")
                    st.error(traceback.format_exc())

if __name__ == "__main__":
    main()
