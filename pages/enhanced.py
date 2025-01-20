import streamlit as st
from wand.image import Image

# Title and Description
st.title("SVG to PNG Converter")
st.write("Upload an SVG file, and this app will convert it to a PNG file.")

# File Upload
uploaded_file = st.file_uploader("Upload SVG File here", type="svg")

if uploaded_file is not None:
    try:
        # Convert SVG to PNG
        with Image(blob=uploaded_file.read(), format="svg", resolution=300) as img:
            img.background_color = "white"
            img.colorspace = "srgb"
            img.alpha_channel = 'remove'
            img.format = "png"
            png_data = img.make_blob()
        
        # Show success message
        st.success("Conversion successful! Click the button below to download your PNG file.")
        
        # Download Button
        st.download_button(
            label="Download PNG",
            data=png_data,
            file_name="converted_image.png",
            mime="image/png"
        )
    except Exception as e:
        # Error handling
        st.error(f"An error occurred during conversion: {e}")
