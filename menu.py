import streamlit as st

def menu():
    st.sidebar.title("Navigation")
    
    # Use session state to keep track of the current page
    if "page" not in st.session_state:
        st.session_state.page = "Page 1"

    # Render buttons in the sidebar
    if st.sidebar.button("Page 1"):
        st.session_state.page = "Page 1"
    if st.sidebar.button("Page 2"):
        st.session_state.page = "Page 2"
    
    # Display the selected page
    if st.session_state.page == "Page 1":
        import pages.page1 as page1
        page1.show()
    elif st.session_state.page == "Page 2":
        import pages.page2 as page2
        page2.show()
