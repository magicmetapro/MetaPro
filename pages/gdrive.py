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

# Function to save metadata to CSV
def save_metadata_to_csv(metadata_list, output_path):
    csv_rows = []
    for metadata in metadata_list:
        row = {
            'Filename': metadata.get('Filename', ''),
            'Title': metadata.get('Title', ''),
            'Keywords': metadata.get('Tags', ''),
            'Category': metadata.get('Category', 'N/A'),  # Placeholder for category
            'Release(s)': metadata.get('Releases', 'N/A')  # Placeholder for releases
        }
        csv_rows.append(row)
    
    df = pd.DataFrame(csv_rows)
    df.to_csv(output_path, index=False)
    return output_path

# Main function
def main():
    # Existing code unchanged
    ...
    # Add save metadata step after processing
    if metadata_list:
        csv_file_path = os.path.join(tempfile.gettempdir(), 'metadata.csv')
        save_metadata_to_csv(metadata_list, csv_file_path)
        with open(csv_file_path, 'rb') as csv_file:
            st.download_button(
                label="Download Metadata CSV",
                data=csv_file,
                file_name="metadata.csv",
                mime="text/csv"
            )

if __name__ == '__main__':
    main()
