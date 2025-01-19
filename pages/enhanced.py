import streamlit as st
import os
import tempfile
from PIL import Image
import cairosvg
import google.generativeai as genai
import zipfile
import traceback
import re
import unicodedata
from xml.etree import ElementTree as ET
import csv

st.set_option("client.showSidebarNavigation", False)

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

# Function to convert SVG to JPG
def svg_to_jpg(svg_path, output_path):
    try:
        # Convert SVG to PNG first
        png_output_path = output_path.replace(".svg", ".png")
        cairosvg.svg2png(url=svg_path, write_to=png_output_path, dpi=300)

        # Convert PNG to JPG
        img = Image.open(png_output_path)
        jpg_output_path = png_output_path.replace(".png", ".jpg")
        img = img.convert("RGB")
        img.save(jpg_output_path, "JPEG")

        return jpg_output_path
    except Exception as e:
        st.error(f"Failed to convert SVG to JPG: {e}")
        st.error(traceback.format_exc())
        return None

# Function to generate metadata for images or SVGs using AI model
def generate_metadata(model, content, filename):
    try:
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
            trimmed_tags.strip()
        ]

        return metadata_row
    except Exception as e:
        st.error(f"Failed to generate metadata: {e}")
        st.error(traceback.format_exc())
        return None

# Function to save metadata to a CSV file
def save_metadata_to_csv(metadata_rows):
    csv_file_path = os.path.join(tempfile.gettempdir(), 'metadata.csv')
    try:
        with open(csv_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Filename', 'Title', 'Keywords'])  # CSV header
            writer.writerows(metadata_rows)  # Write metadata rows

        return csv_file_path
    except Exception as e:
        st.error(f"An error occurred while saving CSV: {e}")
        st.error(traceback.format_exc())
        return None

# Main function
def main():
    st.title("SVG to JPG Converter with Metadata Generation")

    api_key = st.text_input('Enter your API Key', type='password')

    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        uploaded_files = st.file_uploader('Upload Images or SVGs', accept_multiple_files=True)

        if uploaded_files:
            if st.button("Process"):
                with st.spinner("Processing..."):
                    metadata_rows = []
                    processed_files = []

                    for file in uploaded_files:
                        temp_path = os.path.join(tempfile.gettempdir(), file.name)
                        with open(temp_path, 'wb') as f:
                            f.write(file.read())

                        if file.type == 'image/svg+xml':
                            jpg_path = svg_to_jpg(temp_path, temp_path)
                            if not jpg_path:
                                continue
                            content = extract_svg_content(temp_path)
                        else:
                            img = Image.open(temp_path)
                            jpg_path = temp_path
                            content = f"An image with dimensions {img.size}"

                        metadata_row = generate_metadata(model, content, os.path.basename(jpg_path))
                        if metadata_row:
                            metadata_rows.append(metadata_row)
                            processed_files.append(jpg_path)

                    csv_path = save_metadata_to_csv(metadata_rows)
                    if csv_path:
                        with open(csv_path, 'rb') as csv_file:
                            st.download_button("Download Metadata CSV", csv_file, "metadata.csv", "application/csv")

if __name__ == '__main__':
    main()
