import streamlit as st
from svglib.svgnose import svg2rlg
from reportlab.graphics.renderPM import drawToString
from PIL import Image
import io

# Streamlit App
st.title("SVG to JPG Converter")

# Upload SVG file
uploaded_file = st.file_uploader("Choose an SVG file", type="svg")

if uploaded_file is not None:
    # Read the SVG file
    svg_data = uploaded_file.read()

    try:
        # Convert the SVG to a drawing object
        drawing = svg2rlg(io.BytesIO(svg_data))
        
        # Convert the drawing to a PNG (in memory)
        png_data = drawToString(drawing, fmt='PNG')

        # Open the PNG data using Pillow
        image = Image.open(io.BytesIO(png_data))
        
        # Convert PNG to JPG
        with io.BytesIO() as output:
            image.convert("RGB").save(output, format="JPEG")
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
