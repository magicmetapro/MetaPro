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
import xml.etree.ElementTree as ET

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

# Function to embed metadata into images and rename based on title
def embed_metadata(image_path, metadata):
    try:
        if image_path.endswith('.svg'):
            return embed_metadata_svg(image_path, metadata)

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

        # Rename the file based on the generated title
        base_dir = os.path.dirname(image_path)
        normalized_title = normalize_text(metadata['Title'])
        new_image_path = os.path.join(base_dir, f"{normalized_title}.jpg")

        # Ensure unique file names
        counter = 1
        while os.path.exists(new_image_path):
            new_image_path = os.path.join(base_dir, f"{normalized_title}_{counter}.jpg")
            counter += 1

        os.rename(image_path, new_image_path)

        return new_image_path

    except Exception as e:
        st.error(f"An error occurred while embedding metadata: {e}")
        st.error(traceback.format_exc())  # Print detailed error traceback for debugging

# Function to embed metadata into SVG
def embed_metadata_svg(svg_path, metadata):
    try:
        # Parse the SVG file
        tree = ET.parse(svg_path)
        root = tree.getroot()
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        
        # Find or create <metadata> tag
        metadata_element = root.find('{http://www.w3.org/2000/svg}metadata')
        if metadata_element is None:
            metadata_element = ET.SubElement(root, 'metadata')
        
        # Clear existing metadata
        metadata_element.clear()
        
        # Add title as a direct child of <metadata>
        title_element = ET.SubElement(metadata_element, 'title')
        title_element.text = metadata.get('Title', '')

        # Add keywords as a custom child
        keywords_element = ET.SubElement(metadata_element, 'keywords')
        keywords_element.text = metadata.get('Tags', '')

        # Save the updated SVG to a new file
        new_svg_path = svg_path.rsplit('.', 1)[0] + '_updated.svg'
        tree.write(new_svg_path, encoding='utf-8', xml_declaration=True)
        
        return new_svg_path

    except Exception as e:
        st.error(f"An error occurred while embedding metadata into SVG: {e}")
        st.error(traceback.format_exc())
        return None


# Function to zip processed images
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

# Function to convert images to JPEG
def convert_to_jpeg(image_path):
    try:
        # Open the image
        img = Image.open(image_path)

        # Check if the image is already in JPEG format, if not convert it
        if img.format != 'JPEG':
            # Convert the image to RGB before saving it as JPEG (necessary for PNG images)
            img = img.convert('RGB')

            # Create a new path for the JPEG file
            jpeg_image_path = image_path.rsplit('.', 1)[0] + '.jpg'

            # Save the image as JPEG with 100% quality
            img.save(jpeg_image_path, 'JPEG', quality=100)
            return jpeg_image_path
        else:
            # If the image is already in JPEG format, return the original path
            return image_path
    except Exception as e:
        raise Exception(f"An error occurred while converting the image: {e}")

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

        # Upload image files
        uploaded_files = st.file_uploader('Upload Images (Only JPG, PNG, JPEG, and SVG Supported)', accept_multiple_files=True)

        if uploaded_files:
            valid_files = [file for file in uploaded_files if file.type in ['image/jpeg', 'image/png', 'image/svg+xml']]
            if not valid_files:
                st.error("No valid files uploaded. Please upload JPG, PNG, JPEG, or SVG files.")

            if st.button("Process"):
                if api_key:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    with st.spinner("Processing..."):
                        try:
                            # Check daily upload count
                            upload_date = st.session_state['upload_count']['date']
                            upload_count = st.session_state['upload_count']['count']

                            if upload_date != datetime.now(JAKARTA_TZ).date():
                                upload_count = 0
                                upload_date = datetime.now(JAKARTA_TZ).date()

                            if upload_count + len(valid_files) > 45:
                                st.error("Daily upload limit exceeded. Please try again tomorrow.")
                                return

                            temp_dir = tempfile.mkdtemp()
                            processed_images = []
                            for file in valid_files:
                                file_path = os.path.join(temp_dir, file.name)
                                with open(file_path, 'wb') as f:
                                    f.write(file.read())

                                if file.type == 'image/svg+xml':
                                    metadata = generate_metadata(model, file_path)
                                    processed_path = embed_metadata_svg(file_path, metadata)
                                else:
                                    jpeg_path = convert_to_jpeg(file_path)
                                    metadata = generate_metadata(model, jpeg_path)
                                    processed_path = embed_metadata(jpeg_path, metadata)

                                if processed_path:
                                    processed_images.append(processed_path)

                            if processed_images:
                                # Update session state
                                st.session_state['upload_count']['date'] = upload_date
                                st.session_state['upload_count']['count'] = upload_count + len(valid_files)

                                # Zip the processed images
                                zip_path = zip_processed_images(processed_images)
                                with open(zip_path, 'rb') as f:
                                    st.download_button("Download Processed Images", f, file_name="processed_images.zip")
                            else:
                                st.error("No images were processed.")
                        except Exception as e:
                            st.error("An error occurred during processing. Please try again.")
                            st.error(traceback.format_exc())
                else:
                    st.error("API Key is required.")

if __name__ == '__main__':
    main()
