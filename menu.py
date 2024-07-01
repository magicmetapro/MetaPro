import streamlit as st

def menu_with_redirect():
    # Implement your redirection logic here
    # For example, check if the user is logged in, if not, redirect to login page
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.warning("You need to log in to access this page.")
        st.stop()  # Stop the execution if the user is not logged in

    # If logged in, show the navigation menu
    st.sidebar.title("Navigation")

    if "page" not in st.session_state:
        st.session_state.page = "GDrive"

    if st.sidebar.button("GDrive", key="gdrive", help="Go to GDrive"):
        st.session_state.page = "GDrive"
    if st.sidebar.button("Page 2", key="page2", help="Go to Page 2"):
        st.session_state.page = "Page 2"
    if st.sidebar.button("Page 3", key="page3", help="Go to Page 3"):
        st.session_state.page = "Page 3"
    if st.sidebar.button("Page 4", key="page4", help="Go to Page 4"):
        st.session_state.page = "Page 4"
    if st.sidebar.button("Page 5", key="page5", help="Go to Page 5"):
        st.session_state.page = "Page 5"

    # Display the selected page
    if st.session_state.page == "GDrive":
        import pages.gdrive as gdrive
        gdrive.main()
    elif st.session_state.page == "Page 2":
        import pages.page2 as page2
        page2.show()
    elif st.session_state.page == "Page 3":
        import pages.page3 as page3
        page3.show()
    elif st.session_state.page == "Page 4":
        import pages.page4 as page4
        page4.show()
    elif st.session_state.page == "Page 5":
        import pages.page5 as page5
        page5.show()
