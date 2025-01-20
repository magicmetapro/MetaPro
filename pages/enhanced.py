import streamlit as st
import os
import tempfile
import csv
from PIL import Image
from wand.image import Image as WandImage
import google.generativeai as genai
from datetime import datetime, timedelta
import pytz
import re
import unicodedata
import traceback
import math

# Initialize Streamlit
st.set_option("client.showSidebarNavigation", False)

# Initialize session state
if 'license_validated' not in st.session_state:
    st.session_state['license_validated'] = False

if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

# Normalize text function
def normalize_text(text, max_length=100):
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\s]', '', normalized).strip()
    return cleaned[:max_length]

# Generate metadata function
def generate_metadata_batch(model, png_file_paths):
    metadata_list = []
    try:
        for png_path in png_file_paths:
            with Image.open(png_path) as img:
                # Generate title
                caption = model.generate_content([
                    "Analyze the uploaded image and generate a clear, descriptive, and professional one-line title suitable for a microstock image. The title should summarize the main subject, setting, key themes, and concepts, incorporating potential keywords for searches. Ensure it captures all relevant aspects, including actions, objects, emotions, environment, and context.",
                    img
                ])

                # Generate keywords
                tags = model.generate_content([
                    "Analyze the uploaded image and generate a comprehensive list of 45–50 relevant and specific keywords that encapsulate all aspects of the image, such as actions, objects, emotions, environment, and context. The first five keywords must be the most relevant. Ensure each keyword is a single word, separated by commas, and optimized for searchability and relevance.",
                    img
                ])

                filtered_tags = re.sub(r'[^\w\s,]', '', tags.text)
                keywords = filtered_tags.split(',')[:49]
                trimmed_tags = ','.join(keywords)

                metadata_list.append({
                    'Title': caption.text.strip(),
                    'Keywords': trimmed_tags.strip()
                })
        return metadata_list
    except Exception as e:
        st.error(f"Error generating metadata: {e}")
        st.error(traceback.format_exc())
        return None

# Convert SVG to PNG function
def convert_svg_to_png(svg_file_path):
    try:
        png_file_path = svg_file_path.rsplit('.', 1)[0] + '.png'
        with WandImage(filename=svg_file_path, format='svg') as img:
            img.background_color = "white"
            img.alpha_channel = 'remove'
            img.format = "png"
            img.save(filename=png_file_path)
        return png_file_path
    except Exception as e:
        st.error(f"Error converting SVG to PNG: {e}")
        st.error(traceback.format_exc())
        return None

# Process files in chunks
def process_files_in_chunks(model, svg_file_paths, chunk_size=6):
    results = []
    for i in range(0, len(svg_file_paths), chunk_size):
        batch = svg_file_paths[i:i + chunk_size]
        st.write(f"Processing files {i + 1} to {min(i + chunk_size, len(svg_file_paths))}...")
        png_file_paths = [convert_svg_to_png(svg_file) for svg_file in batch]
        png_file_paths = [path for path in png_file_paths if path]  # Filter out failed conversions
        if png_file_paths:
            metadata = generate_metadata_batch(model, png_file_paths)
            if metadata:
                for j, data in enumerate(metadata):
                    results.append({
                        'Filename': os.path.basename(batch[j]),
                        'Title': data['Title'],
                        'Keywords': data['Keywords'],
                        'Category': 3,  # Placeholder for category
                        'Releases': "Placeholder Name 1, Placeholder Name 2"  # Placeholder for releases
                    })
    return results

# Main function
def main():
    st.title("Metadata Generator (Batch Processing)")

    # License validation logic
    if not st.session_state['license_validated']:
        license_key = st.text_input("Enter your license key:", type="password")
        if st.button("Validate License"):
            if license_key == "a":
                st.session_state['license_validated'] = True
            else:
                st.error("Invalid license key.")
        return

    # API key input
    api_key = st.text_input("Enter your API Key:", value=st.session_state['api_key'] or '')
    if api_key:
        st.session_state['api_key'] = api_key

    # Upload SVG files
    uploaded_files = st.file_uploader("Upload SVG Files (Max: 100)", type="svg", accept_multiple_files=True)

    if uploaded_files and st.button("Process SVG Files"):
        with st.spinner("Processing..."):
            try:
                # Configure AI model
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')

                # Temporary directory for processing
                with tempfile.TemporaryDirectory() as temp_dir:
                    csv_file_path = os.path.join(temp_dir, "metadata.csv")

                    # Save uploaded files to temporary directory
                    svg_file_paths = []
                    for svg_file in uploaded_files:
                        temp_svg_path = os.path.join(temp_dir, svg_file.name)
                        with open(temp_svg_path, 'wb') as temp_file:
                            temp_file.write(svg_file.read())
                        svg_file_paths.append(temp_svg_path)

                    # Process files in chunks and generate metadata
                    results = process_files_in_chunks(model, svg_file_paths, chunk_size=6)

                    # Write results to CSV
                    with open(csv_file_path, 'w', newline='') as csvfile:
                        fieldnames = ['Filename', 'Title', 'Keywords', 'Category', 'Releases']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(results)

                    # Allow CSV download
                    with open(csv_file_path, 'rb') as csv_file:
                        st.download_button(
                            label="Download Metadata CSV",
                            data=csv_file,
                            file_name="metadata.csv",
                            mime="text/csv"
                        )

            except Exception as e:
                st.error(f"An error occurred: {e}")
                st.error(traceback.format_exc())

if __name__ == "__main__":
    main()
