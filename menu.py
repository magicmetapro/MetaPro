import streamlit as st
from pages import gdrive, sftp, prompts, enhanced

def menu():
    # Create a sidebar for navigation
    st.sidebar.title("Navigation")
    
    # Define a dictionary of page names and corresponding functions
    pages = {
        "Google Drive": gdrive.show,
        "SFTP": sftp.show,
        "Prompts": prompts.show,
        "Enhanced": enhanced.show
    }
    
    # Get user selection from the sidebar
    selection = st.sidebar.radio("Go to", list(pages.keys()))
    
    # Call the function associated with the selected page
    pages[selection]()

    # Display additional menu information or links
    st.sidebar.markdown("## Additional Links")
    st.sidebar.markdown("[Streamlit Documentation](https://docs.streamlit.io)")
    st.sidebar.markdown("[GitHub Repository](https://github.com)")

# Assuming the following functions are defined in the respective page modules:
# gdrive.py, sftp.py, prompts.py, enhanced.py
