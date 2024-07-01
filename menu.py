import streamlit as st

def menu():
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Select a page", ["Page 1", "Page 2"])

    if page == "Page 1":
        import pages.page1 as page1
        page1.show()
    elif page == "Page 2":
        import pages.page2 as page2
        page2.show()
