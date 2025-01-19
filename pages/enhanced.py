import streamlit as st
from wand.image import Image
import io

# Streamlit App
st.title("SVG to JPG Converter")

# Upload SVG file
uploaded_file = st.file_uploader("Choose an SVG file", type="svg")

if uploaded_file is not None:
    # Read the SVG file
    svg_data = uploaded_file.read()

    try:
        # Convert SVG to JPG using wand
        with Image(file=io.BytesIO(svg_data)) as img:
            img.format = 'jpg'  # Specify that the output format should be JPG
            with io.BytesIO() as output:
                img.save(file=output)  # Save the output as JPG in memory
                jpg_data = output.getvalue()

        # Provide the download link for the JPG
        st.download_button(
            label="Download JPG",
            data=jpg_data,
            file_name="converted_image.jpg",
            mime="image/jpeg"
        )
    
    except Exception as e:
        st.error(f"An error occurred while converting the SVG: {e}")
