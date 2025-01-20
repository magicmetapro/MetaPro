import streamlit as st
import os
import tempfile
import csv
import time
from multiprocessing import Pool
from PIL import Image
from wand.image import Image as WandImage
import google.generativeai as genai
import re
import unicodedata
import traceback

# Initialize Streamlit
st.set_option("client.showSidebarNavigation", False)

# Initialize session state
if 'license_validated' not in st.session_state:
    st.session_state['license_validated'] = False

if 'api_keys' not in st.session_state:
    st.session_state['api_keys'] = []

# Normalize text function
def normalize_text(text, max_length=100):
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\s]', '', normalized).strip()
    return cleaned[:max_length]

# Generate metadata function
def generate_metadata(model, img_path):
    try:
        with Image.open(img_path) as img:
            # Generate title
            caption = model.generate_content([
                "langsung title , generate in a clear, descriptive, and professional one-line title suitable for a microstock image. The title should summarize the main subject, setting, key themes, and concepts, incorporating potential keywords for searches. Ensure it captures all relevant aspects, including actions, objects, emotions, environment, and context.",
                img
            ])
            # Generate keywords
            tags = model.generate_content([
                "generate a comprehensive list of 45–50 relevant and specific keywords that encapsulate all aspects of the image, such as actions, objects, emotions, environment, and context. The first five keywords must be the most relevant. Ensure each keyword is a single word, separated by commas, and optimized for searchability and relevance.",
                img
            ])
            filtered_tags = re.sub(r'[^\w\s,]', '', tags.text)
            keywords = filtered_tags.split(',')[:49]
            trimmed_tags = ','.join(keywords)
            return {
                'Title': caption.text.strip(),
                'Keywords': trimmed_tags.strip()
            }
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

# Process a single file
def process_file(args):
    api_key, svg_file_path = args
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Convert SVG to PNG
        png_file_path = convert_svg_to_png(svg_file_path)
        if not png_file_path:
            return None

        # Generate metadata
        metadata = generate_metadata(model, png_file_path)
        if metadata:
            return {
                'Filename': os.path.basename(svg_file_path),
                'Title': metadata['Title'],
                'Keywords': metadata['Keywords'],
                'Category': 3,  # Placeholder
                'Releases': "Placeholder Name 1, Placeholder Name 2"  # Placeholder
            }
    except Exception as e:
        st.error(f"Error processing file {svg_file_path}: {e}")
        st.error(traceback.format_exc())
        return None

# Main function
def main():
    st.title("Batch Metadata Generator with Delay and Multiprocessing")

    # License validation
    if not st.session_state['license_validated']:
        license_key = st.text_input("Enter your license key:", type="password")
        if st.button("Validate License"):
            if license_key == "a":
                st.session_state['license_validated'] = True
            else:
                st.error("Invalid license key.")
        return

    # API keys input
    api_keys_input = st.text_area("Enter your API keys (one per line):")
    if api_keys_input:
        st.session_state['api_keys'] = api_keys_input.splitlines()

    if not st.session_state['api_keys']:
        st.error("Please provide at least one API key.")
        return

    # Upload SVG files
    uploaded_files = st.file_uploader("Upload SVG Files (Max: 100)", type="svg", accept_multiple_files=True)

    if uploaded_files and st.button("Process SVG Files"):
        with st.spinner("Processing..."):
            try:
                # Temporary directory for processing
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Save uploaded files to temporary directory
                    svg_file_paths = []
                    for svg_file in uploaded_files:
                        temp_svg_path = os.path.join(temp_dir, svg_file.name)
                        with open(temp_svg_path, 'wb') as temp_file:
                            temp_file.write(svg_file.read())
                        svg_file_paths.append(temp_svg_path)

                    # Prepare arguments for multiprocessing
                    api_keys = st.session_state['api_keys']
                    args = [(api_keys[i % len(api_keys)], file) for i, file in enumerate(svg_file_paths)]

                    # Process files in parallel
                    results = []
                    with Pool(processes=4) as pool:  # Adjust number of processes as needed
                        results = pool.map(process_file, args)

                    # Filter None results
                    results = [res for res in results if res]

                    # Save results to CSV
                    csv_file_path = os.path.join(temp_dir, "metadata.csv")
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
