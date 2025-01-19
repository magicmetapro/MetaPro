import streamlit as st
from cairosvg import svg2png
from io import BytesIO

def main():
    st.title("SVG to PNG Converter")
    st.write("Upload an SVG file, and this tool will convert it to a PNG image.")

    # File uploader
    uploaded_file = st.file_uploader("Upload SVG file", type=["svg"])

    if uploaded_file:
        try:
            # Convert SVG to PNG
            svg_content = uploaded_file.read()
            png_output = BytesIO()
            svg2png(bytestring=svg_content, write_to=png_output)

            # Display the PNG
            st.image(png_output.getvalue(), format="PNG")

            # Provide download link for the PNG file
            st.download_button(
                label="Download PNG",
                data=png_output.getvalue(),
                file_name="converted_image.png",
                mime="image/png"
            )

        except Exception as e:
            st.error(f"An error occurred during the conversion: {e}")

if __name__ == "__main__":
    main()
