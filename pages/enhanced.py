import streamlit as st
from menu import menu_with_redirect

# Set the page configuration first
st.set_page_config(page_title="MetaPro", page_icon="🪐")

# Disable sidebar navigation
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

st.markdown(
    """
    <style>
    .main {
        background-color: #FFFFFF;
        color: #2e2e2e;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
    }
    .coming-soon {
        font-size: 50px;
        font-weight: bold;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="main"><div class="coming-soon">Coming Soon</div></div>', unsafe_allow_html=True)
