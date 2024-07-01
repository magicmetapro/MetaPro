import streamlit as st

def menu():
    st.sidebar.title("Navigation")

    # Use session state to keep track of the current page
    if "page" not in st.session_state:
        st.session_state.page = "Page 1"

    # Custom CSS for styling the buttons
    st.markdown("""
        <style>
        .sidebar-button {
            background-color: #4CAF50; /* Green */
            border: none;
            color: white;
            padding: 10px 20px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            transition-duration: 0.4s;
            cursor: pointer;
            width: 100%;
        }

        .sidebar-button:hover {
            background-color: white; 
            color: black; 
            border: 2px solid #4CAF50;
        }

        .spacing {
            margin-top: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Render buttons in the sidebar
    if st.sidebar.button("Page 1", key="page1", help="Go to Page 1"):
        st.session_state.page = "Page 1"
    st.sidebar.markdown('<div class="spacing"></div>', unsafe_allow_html=True)  # Add space between buttons
    if st.sidebar.button("Page 2", key="page2", help="Go to Page 2"):
        st.session_state.page = "Page 2"

    # Display the selected page
    if st.session_state.page == "Page 1":
        import pages.page1 as page1
        page1.show()
    elif st.session_state.page == "Page 2":
        import pages.page2 as page2
        page2.show()
