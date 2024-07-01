import streamlit as st

def authenticated_menu():
    # Show a navigation menu for authenticated users
    st.sidebar.page_link("app.py", label="Home", icon="🏠")
    st.sidebar.page_link("pages/gdrive.py", label="Upload via Gdrive", icon="🌍")
    st.sidebar.page_link("pages/sftp.py", label="Upload via SFTP", icon="🚀")
    st.sidebar.page_link("pages/prompts.py", label="Magic Prompts", icon="✨")
    st.sidebar.page_link("pages/enhanced.py", label="Enhanced Images", icon="🖼️")

    # Add dropdown list at the bottom of the sidebar
    st.sidebar.selectbox("Select an option", ["text1", "text2", "text3", "text4", "text5", "text6", "text7", "text8", "text9", "text10"])
    

def unauthenticated_menu():
    # Show a navigation menu for unauthenticated users
    st.sidebar.page_link("app.py", label="Log in", icon="🔒")

    # Add dropdown list at the bottom of the sidebar
    st.sidebar.selectbox("Select an option", ["text1", "text2", "text3", "text4", "text5", "text6", "text7", "text8", "text9", "text10"])


def menu():
    # Determine if a user is logged in or not, then show the correct
    # navigation menu
    if "role" not in st.session_state or st.session_state.role is None:
        unauthenticated_menu()
        return
    authenticated_menu()


def menu_with_redirect():
    # Redirect users to the main page if not logged in, otherwise continue to
    # render the navigation menu
    if "role" not in st.session_state or st.session_state.role is None:
        st.switch_page("app.py")
    menu()

# Call the menu_with_redirect function
menu_with_redirect()
