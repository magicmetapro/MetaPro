import streamlit as st
import os
import tempfile
import cairosvg
from PIL import Image
import google.generativeai as genai
import re
import traceback
import unicodedata
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

if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

# Function to normalize text
def normalize_text(text, max_length=100):
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\s]', '', normalized).strip()
    return cleaned[:max_length]  # Truncate to the specified max length

# Function to convert SVG to PNG
def convert_svg_to_png(svg_file_path):
    output_png_path = tempfile.mktemp(suffix=".png")  # Create a temporary PNG file path
    cairosvg.svg2png(url=svg_file_path, write_to=output_png_path)  # Convert SVG to PNG
    return output_png_path

# Function to generate metadata (title and keywords)
def generate_metadata(model, img_path):
    caption = model.generate_content([
        "Analyze the uploaded image and generate a clear, descriptive, and professional one-line title suitable for a microstock image. The title should summarize the main subject, setting, key themes, and concepts, incorporating potential keywords for searches. Ensure it captures all relevant aspects, including actions, objects, emotions, environment, and context.",
        img_path
    ])
    tags = model.generate_content([
        "Analyze the uploaded image and generate a comprehensive list of 45–50 relevant and specific keywords that encapsulate all aspects of the image, such as actions, objects, emotions, environment, and context. The first five keywords must be the most relevant. Ensure each keyword is a single word, separated by commas, and optimized for searchability and relevance.",
        img_path
    ])

    # Filter out undesirable characters from the generated tags
    filtered_tags = re.sub(r'[^\w\s,]', '', tags.text)
    # Limit the generated keywords to 49 words
    keywords = filtered_tags.split(',')[:49]  # Limit to 49 words
    trimmed_tags = ','.join(keywords)

    return {
        'Title': caption.text.strip(),  # Remove leading/trailing whitespace
        'Tags': trimmed_tags.strip()
    }

# Write metadata to CSV
def write_metadata_to_csv(metadata_list, output_path):
    import csv
    with open(output_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['Title', 'Tags'])
        writer.writeheader()
        for data in metadata_list:
            writer.writerow(data)

# Write metadata to TXT
def write_metadata_to_txt(metadata_list, output_path):
    with open(output_path, 'w', encoding='utf-8') as file:
        for data in metadata_list:
            file.write(f"Title: {data['Title']}\n")
            file.write(f"Tags: {data['Tags']}\n")
            file.write("\n" + "-"*30 + "\n")

# Main function
def main():
    """Main function for the Streamlit app."""
    st.markdown("""
    <div style="text-align: center; margin-top: 20px;">
        <a href="https://wa.me/6282265298845" target="_blank">
            <button style="background-color: #1976d2; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
                MetaPro
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)

    # License validation and API key input
    api_key = st.text_input('Enter your [API](https://makersuite.google.com/app/apikey) Key', value=st.session_state['api_key'] or '')

    # Save API key in session state
    if api_key:
        st.session_state['api_key'] = api_key

    # Upload SVG files
    uploaded_files = st.file_uploader('Upload SVG Images', type='svg', accept_multiple_files=True)

    if uploaded_files:
        valid_files = [file for file in uploaded_files if file.type == 'image/svg+xml']
        if valid_files and st.button("Process"):
            with st.spinner("Processing..."):
                try:
                    # Configure AI model with API key
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')

                    # Create a temporary directory to store the uploaded images
                    with tempfile.TemporaryDirectory() as temp_dir:
                        image_paths = []
                        metadata_list = []

                        # Process each SVG file
                        for file in valid_files:
                            temp_svg_path = os.path.join(temp_dir, file.name)
                            with open(temp_svg_path, 'wb') as f:
                                f.write(file.read())

                            # Convert SVG to PNG
                            png_image_path = convert_svg_to_png(temp_svg_path)

                            # Generate metadata for the converted PNG
                            metadata = generate_metadata(model, png_image_path)
                            metadata_list.append(metadata)

                            # Display the result below the processing section
                            st.markdown(f"**Title:** {metadata['Title']}")
                            st.markdown(f"**Tags:** {metadata['Tags']}")

                        # Write metadata to CSV and TXT
                        output_csv_path = os.path.join(temp_dir, 'metadata.csv')
                        write_metadata_to_csv(metadata_list, output_csv_path)

                        output_txt_path = os.path.join(temp_dir, 'metadata.txt')
                        write_metadata_to_txt(metadata_list, output_txt_path)

                        # Provide download buttons for the CSV and TXT
                        with open(output_csv_path, 'rb') as csv_file:
                            st.download_button(
                                label="Download Metadata CSV",
                                data=csv_file,
                                file_name="metadata.csv",
                                mime="text/csv"
                            )

                        with open(output_txt_path, 'rb') as txt_file:
                            st.download_button(
                                label="Download Metadata TXT",
                                data=txt_file,
                                file_name="metadata.txt",
                                mime="text/plain"
                            )

                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    st.error(traceback.format_exc())  # Print detailed error traceback for debugging

if __name__ == '__main__':
    main()
