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
import cairosvg
from menu import menu_with_redirect
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from PIL import Image
from PIL import Image as PILImage

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

    filtered_tags = re.sub(r'[^\w\s,]', '', tags.text)
    keywords = filtered_tags.split(',')[:49]  # Limit to 49 words
    trimmed_tags = ','.join(keywords)

    return {
        'Title': caption.text.strip(),
        'Tags': trimmed_tags.strip()
    }

# Function to embed metadata into images and rename based on title
def embed_metadata(image_path, metadata):
    try:
        time.sleep(1)
        img = Image.open(image_path)
        iptc_data = iptcinfo3.IPTCInfo(image_path, force=True)
        for tag in iptc_data._data:
            iptc_data._data[tag] = []
        iptc_data['keywords'] = [metadata.get('Tags', '')]
        iptc_data['caption/abstract'] = [metadata.get('Title', '')]
        iptc_data.save()

        base_dir = os.path.dirname(image_path)
        normalized_title = normalize_text(metadata['Title'])
        new_image_path = os.path.join(base_dir, f"{normalized_title}.jpg")

        counter = 1
        while os.path.exists(new_image_path):
            new_image_path = os.path.join(base_dir, f"{normalized_title}_{counter}.jpg")
            counter += 1

        os.rename(image_path, new_image_path)
        return new_image_path

    except Exception as e:
        st.error(f"An error occurred while embedding metadata: {e}")
        st.error(traceback.format_exc())

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

# Function to convert SVG to JPEG using svglib and reportlab
def convert_svg_to_jpeg(svg_path):
    try:
        # Using svglib to render the SVG
        drawing = svg2rlg(svg_path)
        # Save the rendered SVG as a PNG
        png_path = svg_path.rsplit('.', 1)[0] + '.png'
        renderPM.drawToFile(drawing, png_path, fmt="PNG")
        # Convert the PNG to JPEG using Pillow
        img = Image.open(png_path).convert('RGB')
        jpeg_path = svg_path.rsplit('.', 1)[0] + '.jpg'
        img.save(jpeg_path, 'JPEG', quality=100)
        return jpeg_path
    except Exception as e:
        raise Exception(f"An error occurred while converting SVG to JPEG: {e}")

# Function to convert images to JPEG
def convert_to_jpeg(image_path):
    try:
        img = Image.open(image_path)
        if img.format != 'JPEG':
            img = img.convert('RGB')
            jpeg_image_path = image_path.rsplit('.', 1)[0] + '.jpg'
            img.save(jpeg_image_path, 'JPEG', quality=100)
            return jpeg_image_path
        else:
            return image_path
    except Exception as e:
        raise Exception(f"An error occurred while converting the image: {e}")

# Main function
def main():
    st.markdown("""
    <div style="text-align: center; margin-top: 20px;">
        <a href="https://wa.me/6282265298845" target="_blank">
            <button style="background-color: #1976d2; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
                MetaPro
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)

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

        api_key = st.text_input('Enter your [API](https://makersuite.google.com/app/apikey) Key', value=st.session_state['api_key'] or '')
        if api_key:
            st.session_state['api_key'] = api_key

        uploaded_files = st.file_uploader('Upload Images (Only JPG, PNG, and SVG Supported)', accept_multiple_files=True)

        if uploaded_files:
            valid_files = [file for file in uploaded_files if file.type in ['image/jpeg', 'image/png', 'image/svg+xml']]
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
                            for file in valid_files:
                                temp_image_path = os.path.join(temp_dir, file.name)
                                with open(temp_image_path, 'wb') as f:
                                    f.write(file.read())

                                if file.type == 'image/svg+xml':
                                    jpeg_image_path = convert_svg_to_jpeg(temp_image_path)
                                else:
                                    jpeg_image_path = convert_to_jpeg(temp_image_path)

                                image_paths.append(jpeg_image_path)

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

                            processed_image_paths = []
                            for image_path, metadata in zip(image_paths, metadata_list):
                                updated_image_path = embed_metadata(image_path, metadata)
                                if updated_image_path:
                                    processed_image_paths.append(updated_image_path)

                            zip_file_path = zip_processed_images(processed_image_paths)

                            if zip_file_path:
                                st.success("Processing complete. Download your files below:")
                                with open(zip_file_path, 'rb') as zip_file:
                                    st.download_button(
                                        label="Download Processed Images",
                                        data=zip_file,
                                        file_name="processed_images.zip",
                                        mime="application/zip"
                                    )

                    except Exception as e:
                        st.error(f"An error occurred: {e}")
                        st.error(traceback.format_exc())

if __name__ == '__main__':
    main()
