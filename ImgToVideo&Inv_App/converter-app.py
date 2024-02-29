import streamlit as st

st.set_page_config(
    page_title="Converter",
)

st.write("# Welcome! ")

st.sidebar.success("Select the process you want to do")

st.markdown(
    """
    This is a web application to assist you with converting 
    your videos to images and vice-versa 
    **👈 Select a process from the sidebar** to 
    start working!
    ### Video To Image Converter (:film_projector: :arrow_right: :frame_with_picture:)
    Step 1: Upload the video\n
    Step 2: Select the frame skip rate\n
    Step 3: Download the images or save the images in the drive\n
    
    ### Image To Video Converter (:frame_with_picture: :arrow_right: :film_projector:)
    Step 1: Upload the images\n
    Step 2: Select the frame rate for the video\n
    Step 3: Download the video or save it in the drive\n
"""
)