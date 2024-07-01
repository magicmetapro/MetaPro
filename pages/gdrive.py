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

# Check if the user is authenticated
if not st.session_state.get('authenticated', False):
    st.warning("You need to log in to access this page.")
    st.stop()  # Stop the execution if the user is not logged in

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

# Function to normalize and clean text
def normalize_text(text):
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    return normalized

# Function to generate metadata for images using AI model
def generate_metadata(model, img):
    caption = model.generate_content(["As the helpful Digital Asset Metadata Manager, analyze the following image and generate search engine optimized titles for stock photography. Create a descriptive title in English, up to 12 words long, that identifies the main elements of the image. Highlight the primary subjects, objects, activities, and context. Refine the title to include relevant keywords for SEO, ensuring it is engaging and informative. Avoid mentioning human names, brand names, product names, or company names.", img])
    tags = model.generate_content(["Generate up to 45 keywords in English that are relevant to the image (each keyword must be one word, separated by commas). Ensure each keyword is a single word, separated by commas.", img])

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

        return file.get('webViewLink')
    except Exception as e:
        st.error(f"An error occurred while uploading to Google Drive: {e}")
        st.error(traceback.format_exc())
        return None

def generate_description(model, img):
    description = model.generate_content(["Generate very detailed descriptive description for stock photo related to (Concept). dont use words : The photo shows ", img])
    return description.text.strip()

def format_midjourney_prompt(description):
    prompt_text = f"{description} -ar 16:9"
    return prompt_text

def main():
    """Main function for the Streamlit app."""

    # Display WhatsApp chat link
    st.markdown("""
    <div style="text-align: center; margin-top: 20px;">
        <a href="https://wa.me/6285328007533" target="_blank">
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
            st.success(f"License valid. You have {days_remaining} days remaining. Max 45 files per upload, unlimited daily uploads.")

        # API Key input
        api_key = st.text_input('Enter your [API](https://makersuite.google.com/app/apikey) Key', value=st.session_state['api_key'] or '')

        # Save API key in session state
        if api_key:
            st.session_state['api_key'] = api_key

        # Upload image files
        uploaded_files = st.file_uploader("Upload image files", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

        if uploaded_files:
            if len(uploaded_files) > 45:
                st.error("You can upload a maximum of 45 files at a time.")
                return

            # Initialize AI model
            genai.configure(api_key=api_key)
            model = genai.get_model('model_name')

            # Progress bar
            progress_bar = st.progress(0)
            files_processed = 0

            # Process each uploaded file
            processed_images = []
            for uploaded_file in uploaded_files:
                try:
                    # Save the uploaded file to a temporary location
                    temp_file_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
                    with open(temp_file_path, "wb") as temp_file:
                        temp_file.write(uploaded_file.read())

                    # Generate metadata for the image
                    metadata = generate_metadata(model, temp_file_path)

                    # Embed metadata into the image
                    updated_image_path = embed_metadata(temp_file_path, metadata, progress_bar, files_processed, len(uploaded_files))

                    # Generate description for MidJourney prompt
                    description = generate_description(model, temp_file_path)

                    # Format the description for MidJourney prompt
                    formatted_prompt = format_midjourney_prompt(description)

                    # Store the updated image path and formatted prompt
                    processed_images.append((updated_image_path, formatted_prompt))

                except Exception as e:
                    st.error(f"An error occurred while processing {uploaded_file.name}: {e}")
                    st.error(traceback.format_exc())
                    continue

            # Zip the processed images
            zip_file_path = zip_processed_images([image_path for image_path, _ in processed_images])

            if zip_file_path:
                # Google Drive authentication
                drive_credentials = service_account.Credentials.from_service_account_info(
                    json.loads(st.secrets["GOOGLE_DRIVE_CREDENTIALS"]),
                    scopes=["https://www.googleapis.com/auth/drive.file"]
                )

                # Upload the zip file to Google Drive
                drive_link = upload_to_drive(zip_file_path, drive_credentials)

                if drive_link:
                    st.success("Files processed and uploaded successfully!")
                    st.markdown(f"[Download Processed Images]({drive_link})")

            # Update session state for upload count
            current_date_str = current_date.strftime("%Y-%m-%d")
            if st.session_state['upload_count']['date'] == current_date_str:
                st.session_state['upload_count']['count'] += len(uploaded_files)
            else:
                st.session_state['upload_count'] = {
                    'date': current_date_str,
                    'count': len(uploaded_files)
                }

        # Clear API key and license key input
        if st.button("Clear"):
            st.session_state['api_key'] = None
            st.session_state['license_validated'] = False
            st.session_state['upload_count'] = {
                'date': None,
                'count': 0
            }
            st.experimental_rerun()

if __name__ == "__main__":
    main()
