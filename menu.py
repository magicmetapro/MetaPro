import streamlit as st


def authenticated_menu():
    # Show a navigation menu for authenticated users
    st.sidebar.page_link("app.py", label="Home", icon="🏠")
    st.sidebar.page_link("pages/gdrive.py", label="Upload via Gdrive", icon="🌍")
    st.sidebar.page_link("pages/allcsv.py", label="Allcsv", icon="")
    st.sidebar.page_link("pages/sftp.py", label="Upload via SFTP", icon="🚀")
    st.sidebar.page_link("pages/prompts.py", label="Magic Prompts", icon="✨")
    st.sidebar.page_link("pages/enhanced.py", label="Enhanced Images", icon="🖼️")
    

def unauthenticated_menu():
    # Show a navigation menu for unauthenticated users
    st.sidebar.page_link("app.py", label="Log in", icon="🔒")


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

