import streamlit as st
import os
import tempfile
from PIL import Image
import google.generativeai as genai
import traceback
from datetime import datetime, timedelta
import pytz
from menu import menu_with_redirect
import pandas as pd
from fpdf import FPDF, HTMLMixin

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
        .prompt-title {
            font-size: 14px;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

# Set the timezone to UTC+7 Jakarta
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# Initialize session state for license validation
if 'license_validated' not in st.session_state:
    st.session_state['license_validated'] = False

if 'upload_count' not in st.session_state:
    st.session_state['upload_count'] = {
        'date': None,
        'count': 0
    }

if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

def generate_description(model, img, prompt_template, num_prompts):
    description = model.generate_content([f"{prompt_template} {num_prompts} prompts.", img])
    return description.text.strip()

def save_prompts_to_excel(prompts, similar_prompts, file_path):
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        pd.DataFrame(prompts, columns=["Prompts"]).to_excel(writer, sheet_name='Prompts', index=False)
        pd.DataFrame(similar_prompts, columns=["Similar Prompts"]).to_excel(writer, sheet_name='Similar Prompts', index=False)
    return file_path

class PDF(FPDF, HTMLMixin):
    pass

def save_prompts_to_pdf(prompts, similar_prompts, file_path):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Prompts", ln=True, align="C")
    for prompt in prompts:
        pdf.multi_cell(0, 10, txt=prompt)

    pdf.add_page()
    pdf.cell(200, 10, txt="Similar Prompts", ln=True, align="C")
    for prompt in similar_prompts:
        pdf.multi_cell(0, 10, txt=prompt)

    pdf.output(file_path)
    return file_path

def main():
    """Main function for the Streamlit app."""

    # Display WhatsApp chat link
    st.markdown("""
    <div style="text-align: center; margin-top: 20px;">
        <a href="https://wa.me/6282265298845" target="_blank">
            <button style="background-color: #1976d2; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
                MetaPro
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)

    # Check if license has already been validated
    license_file = "license.txt"
    if not st.session_state['license_validated']:
        if os.path.exists(license_file):
            with open(license_file, 'r') as file:
                start_date_str = file.read().strip()
                start_date = datetime.fromisoformat(start_date_str)
                st.session_state['license_validated'] = True
        else:
            # License key input
            validation_key = st.text_input('License Key', type='password')

    # Check if validation key is correct
    correct_key = "dian12345"

    if not st.session_state['license_validated'] and validation_key:
        if validation_key == correct_key:
            st.session_state['license_validated'] = True
            start_date = datetime.now(JAKARTA_TZ)
            with open(license_file, 'w') as file:
                file.write(start_date.isoformat())
        else:
            st.error("Invalid validation key. Please enter the correct key.")

    if st.session_state['license_validated']:
        # Check the license file for the start date
        with open(license_file, 'r') as file:
            start_date_str = file.read().strip()
            start_date = datetime.fromisoformat(start_date_str)

        # Calculate the expiration date
        expiration_date = start_date + timedelta(days=91)
        current_date = datetime.now(JAKARTA_TZ)

        if current_date > expiration_date:
            st.error("Your license has expired. Please contact support for a new license key.")
            return
        else:
            days_remaining = (expiration_date - current_date).days
            st.success(f"License valid. You have {days_remaining} days remaining.")

        # API Key input
        api_key = st.text_input('Enter your [API](https://makersuite.google.com/app/apikey) Key', value=st.session_state['api_key'] or '')

        # Save API key in session state
        if api_key:
            st.session_state['api_key'] = api_key

        # Hardcoded prompt template
        prompt_template = 'Create prompts for microstock, The prompts must be able to produce images exactly like this one.'

        # Number of prompts to generate
        num_prompts = st.number_input('Enter the number of prompts to generate', min_value=1, max_value=10, value=1)

        # Additional text for prompts
        additional_text = st.text_input('Additional text for prompts', value='--ar 16:9')

        # Number of similar prompts to generate
        num_similar_prompts = st.number_input('Enter the number of similar prompts to generate', min_value=1, max_value=10, value=4)

        # Upload image files
        uploaded_files = st.file_uploader('Upload Images (JPG, JPEG, PNG supported)', type=['jpg', 'jpeg', 'png'], accept_multiple_files=True, key="file_uploader")

        if uploaded_files and st.button("Process"):
            with st.spinner("Processing..."):
                try:
                    # Check and update upload count for the current date
                    if st.session_state['upload_count']['date'] != current_date.date():
                        st.session_state['upload_count'] = {
                            'date': current_date.date(),
                            'count': 0
                        }

                    # Check if remaining uploads are available
                    if st.session_state['upload_count']['count'] >= 1000:
                        remaining_uploads = 0
                        st.warning(f"You have exceeded the upload limit. Remaining uploads for today: {remaining_uploads}")
                        return
                    else:
                        st.session_state['upload_count']['count'] += len(uploaded_files)
                        st.success(f"Upload successful. Remaining uploads for today: {1000 - st.session_state['upload_count']['count']}")

                    genai.configure(api_key=api_key)  # Configure AI model with API key
                    model = genai.GenerativeModel('gemini-1.5-flash')

                    all_prompts = []  # To store all generated prompts
                    similar_prompts = []  # To store all generated similar prompts

                    # Create a temporary directory to store the uploaded images
                    with tempfile.TemporaryDirectory() as temp_dir:
                        for uploaded_file in uploaded_files:
                            # Save the uploaded image to the temporary directory
                            temp_image_path = os.path.join(temp_dir, uploaded_file.name)
                            with open(temp_image_path, 'wb') as f:
                                f.write(uploaded_file.read())

                            # Open the image
                            if temp_image_path:
                                img = Image.open(temp_image_path)

                                # Generate description and prompts
                                description = generate_description(model, img, prompt_template, num_prompts)
                                prompts = [f"{prompt.strip()} {additional_text}" for prompt in description.split("\n") if prompt.strip()]
                                all_prompts.extend(prompts)

                                # Generate similar prompts
                                similar_prompt_template = 'Create similar prompts based on the image. Ensure the prompts lead to popular images on photostock, particularly on Adobe Stock, but make sure they remain similar in concept to those images.'
                                similar_description = generate_description(model, img, similar_prompt_template, num_similar_prompts)
                                similar_prompts_list = [f"{prompt.strip()} {additional_text}" for prompt in similar_description.split("\n") if prompt.strip()]
                                similar_prompts.extend(similar_prompts_list)

                                # Display thumbnail and prompts
                                st.image(img, width=100)
                                st.markdown("<div class='prompt-title'>Prompts</div>", unsafe_allow_html=True)
                                for prompt in prompts:
                                    st.markdown(f"{prompt}\n")

                                st.markdown("<div class='prompt-title'>Similar Prompts</div>", unsafe_allow_html=True)
                                for prompt in similar_prompts_list:
                                    st.markdown(f"{prompt}\n")

                    # Export options
                    st.markdown("### Export Options")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                        combined_excel_file = save_prompts_to_excel(all_prompts, similar_prompts, tmp.name)
                    with open(combined_excel_file, 'rb') as f:
                        st.download_button(
                            label="Download Prompts as Excel",
                            data=f.read(),
                            file_name="prompts.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        combined_pdf_file = save_prompts_to_pdf(all_prompts, similar_prompts, tmp.name)
                    with open(combined_pdf_file, 'rb') as f:
                        st.download_button(
                            label="Download Prompts as PDF",
                            data=f.read(),
                            file_name="prompts.pdf",
                            mime="application/pdf"
                        )

                except Exception as e:
                    st.error("An error occurred while processing the image.")
                    st.error(traceback.format_exc())

if __name__ == "__main__":
    main()
