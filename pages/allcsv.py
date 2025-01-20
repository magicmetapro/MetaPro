import threading
import time
import csv
import os
import re
import traceback
import unicodedata
from PIL import Image
import streamlit as st
import google.generativeai as genai
import tempfile
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

# Function to normalize text
def normalize_text(text, max_length=100):
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\s]', '', normalized).strip()
    return cleaned[:max_length]  # Truncate to the specified max length

# Function to generate metadata for images using the Gemini model
def generate_metadata(model, image_path):
    try:
        with open(image_path, "rb") as image_file:
            img = image_file.read()

        # Use Gemini model to generate title
        caption_response = model.generate_content([
            "Analyze the uploaded image and generate a clear, descriptive, and professional one-line title suitable for a microstock image. The title should summarize the main subject, setting, key themes, and concepts, incorporating potential keywords for searches. Ensure it captures all relevant aspects, including actions, objects, emotions, environment, and context.",
            img
        ])
        title = caption_response.text.strip()

        # Use Gemini model to generate tags (keywords)
        tags_response = model.generate_content([
            "Analyze the uploaded image and generate a comprehensive list of 45–50 relevant and specific keywords that encapsulate all aspects of the image, such as actions, objects, emotions, environment, and context. The first five keywords must be the most relevant. Ensure each keyword is a single word, separated by commas, and optimized for searchability and relevance.",
            img
        ])
        tags = tags_response.text.strip()

        # Filter out undesirable characters from the generated tags
        filtered_tags = re.sub(r'[^\w\s,]', '', tags)

        # Limit the number of keywords to 49
        keywords = filtered_tags.split(',')[:49]
        trimmed_tags = ','.join(keywords)

        return {
            'Title': title,
            'Tags': trimmed_tags
        }
    except Exception as e:
        st.error(f"Error generating metadata for image: {e}")
        return None

# Function to save results to disk
def save_results(results, temp_dir):
    csv_file_path = os.path.join(temp_dir, "processed_metadata.csv")
    with open(csv_file_path, 'w', newline='') as csvfile:
        fieldnames = ['Filename', 'Title', 'Keywords', 'Category', 'Releases']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for result in results:
            writer.writerow(result)

    return csv_file_path

# Function to process a batch of files using threading
def process_batch(model, files_chunk, results, api_key):
    try:
        # Set API key for the current batch
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"Failed to configure API key: {e}")
        return

    for file in files_chunk:
        try:
            # Generate metadata for each image
            metadata = generate_metadata(model, file)
            if metadata:
                # Formatting Releases field as "Name1, Name2, ..."
                releases = "Haleeq Whitten, Ludovic Hillion, Morgan Greentstreet, Christine Manore"
                results.append({
                    'Filename': os.path.basename(file.name),
                    'Title': metadata['Title'],
                    'Keywords': metadata['Tags'],
                    'Category': 3,
                    'Releases': releases
                })
        except Exception as e:
            st.error(f"An error occurred while processing {file.name}: {e}")
            st.error(traceback.format_exc())

# Main function
def main():
    """Main function for the Streamlit app."""
    # Configure the model
    try:
        model = genai.get_model('models/gemini-1.5-flash')
    except Exception as e:
        st.error(f"Failed to initialize the model: {e}")
        st.stop()

    # Image file upload
    uploaded_files = st.file_uploader("Upload image files (JPG, PNG, JPEG, SVG)", accept_multiple_files=True)
    if not uploaded_files:
        st.warning("Please upload some image files to process.")
        return

    # Button to trigger processing
    if st.button("Process All Images"):
        # Split files into batches of 6
        chunks = [uploaded_files[i:i + 6] for i in range(0, len(uploaded_files), 6)]
        threads = []
        results = []
        with tempfile.TemporaryDirectory() as temp_dir:
            api_keys = [
                "AIzaSyBzKrjj-UwAVm-0MEjfSx3ShnJ4fDrsACU", "API_KEY_2", "API_KEY_3", "API_KEY_4", "API_KEY_5", "API_KEY_6"
            ]
            api_key_index = 0

            for chunk in chunks:
                # Rotate API keys for each batch
                current_api_key = api_keys[api_key_index % len(api_keys)]
                api_key_index += 1

                thread = threading.Thread(target=process_batch, args=(model, chunk, results, current_api_key))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()

            # Save results to CSV file
            csv_file_path = save_results(results, temp_dir)

            # Provide download link for the CSV file
            st.success("Processing complete. Download your metadata CSV below:")
            with open(csv_file_path, 'rb') as csv_file:
                st.download_button(
                    label="Download Processed Metadata",
                    data=csv_file,
                    file_name="processed_metadata.csv",
                    mime="application/csv"
                )

if __name__ == '__main__':
    main()
