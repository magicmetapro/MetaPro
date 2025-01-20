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
import iptcinfo3
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

# Function to save partial results to disk
def save_partial_results(results, temp_dir):
    partial_csv = os.path.join(temp_dir, "partial_metadata.csv")
    with open(partial_csv, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Filename', 'Title', 'Keywords', 'Category', 'Releases'])
        for result in results:
            writer.writerow(result)

# Function to process a batch of files using threading
def process_batch(model, files_chunk, temp_dir, results):
    for file in files_chunk:
        try:
            img = Image.open(file)
            metadata = generate_metadata(model, img)
            if metadata:
                results.append({
                    'Filename': os.path.basename(file.name),
                    'Title': metadata['Title'],
                    'Keywords': metadata['Tags'],
                    'Category': 3,
                    'Releases': "Placeholder Name 1, Placeholder Name 2"
                })
            save_partial_results(results, temp_dir)
        except Exception as e:
            st.error(f"An error occurred while processing {file.name}: {e}")
            st.error(traceback.format_exc())

# Main function
def main():
    """Main function for the Streamlit app."""
    # Configure the API key for google.generativeai
    try:
        genai.configure(api_key="YOUR_API_KEY")  # Set your actual API key here
    except Exception as e:
        st.error(f"Failed to configure API key: {e}")
        st.stop()

    # Initialize the model
    try:
        model = genai.get_model('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Failed to initialize the model: {e}")
        st.stop()

    # Example list of uploaded files
    uploaded_files = []  # This should be populated with the actual uploaded files
    uploaded_files.append('path_to_image.jpg')  # Add sample image file for demonstration

    # Split the files into batches of 6
    chunks = [uploaded_files[i:i + 6] for i in range(0, len(uploaded_files), 6)]
    threads = []
    results = []
    with tempfile.TemporaryDirectory() as temp_dir:
        for chunk in chunks:
            thread = threading.Thread(target=process_batch, args=(model, chunk, temp_dir, results))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()

    # Save results to CSV file
    csv_file_path = os.path.join(tempfile.gettempdir(), 'processed_metadata.csv')
    with open(csv_file_path, 'w', newline='') as csvfile:
        fieldnames = ['Filename', 'Title', 'Keywords', 'Category', 'Releases']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for result in results:
            writer.writerow(result)

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
