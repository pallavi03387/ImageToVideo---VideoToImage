import cv2
import streamlit as st
from azure.storage.blob import BlobServiceClient
from io import BytesIO
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from tempfile import NamedTemporaryFile
import os
from zipfile import ZipFile



# Azure Blob Storage Connection
connect_str = st.secrets["connection_str"]
blob_service_client = BlobServiceClient.from_connection_string(connect_str)

# Function to create a folder in Google Drive
def create_folder_in_drive(name):
    gauth = GoogleAuth()
    drive = GoogleDrive(gauth)
    folder = drive.CreateFile({'title': name, 'mimeType': 'application/vnd.google-apps.folder'})
    folder.Upload()
    return folder['id']

# Streamlit app setup
st.set_page_config(
    page_title="Video Frame Extraction",
    page_icon="🎥",
    layout="wide"
)

# Video file uploader
st.header("Extract image frames from video")
video_file = st.file_uploader("Upload a video file...", type=("mp4", "avi", "mov"))
# Frame skip input
frame_skip = int(st.slider("Select Frame Skip", 1, 100, 1))

# Extract frames button and share button
extract_button = st.button("Extract Frames", key="extract_button")
share_button1 = st.button("Share to Drive")
# download_button = st.button("Make zip file", key="download_button")

if "download_button" not in st.session_state:
    st.session_state.download_button = 0

if "share_button" not in st.session_state:
    st.session_state.share_button = 0


# Container name
container_name = "extracted-frames"

# Extract frames and enable share button
if extract_button and video_file:
    # Check if the container exists
    container_client = blob_service_client.get_container_client(container_name)
    if not container_client.exists():
        # Create the container if it doesn't exist
        container_client.create_container()

    # Check if the container is empty
    blob_list = container_client.list_blobs()
    if blob_list:
        for blob in blob_list:
            container_client.get_blob_client(blob.name).delete_blob()

    # Save the video file to a temporary location
    temp_file = NamedTemporaryFile(delete=False)
    temp_file.write(video_file.getvalue())
    temp_file_path = temp_file.name
    temp_file.close()

    # Extract frames and save them to the temporary folder in Azure Blob Storage
    frame_count = 0
    cap = cv2.VideoCapture(temp_file_path)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_skip != 0:
            frame_count += 1
            continue

        # Convert frame to PNG byte stream using OpenCV
        ret, encoded_image = cv2.imencode(".png", frame)
        if not ret:
            continue

        image_stream = BytesIO(encoded_image.tobytes())

        # Upload frame to Azure Blob Storage
        name = f"frame{frame_count}.png"
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=name)
        blob_client.upload_blob(image_stream.read(), blob_type="BlockBlob")

        frame_count += 1
    cap.release()
    os.remove(temp_file_path)
    st.session_state.download_button = 1
    st.session_state.share_button = 1


# Share button functionality
if share_button1:
    if st.session_state.share_button == 1:
        container_client = blob_service_client.get_container_client(container=container_name)
        blob_list = container_client.list_blobs()

        gauth = GoogleAuth()
        drive = GoogleDrive(gauth)
        folder = drive.CreateFile({'title': "Extracted Frames", 'mimeType': 'application/vnd.google-apps.folder'})
        folder.Upload()
        output_folder_id = folder['id']

        if blob_list:
            
            for blob in blob_list:
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob.name)
                download_stream = blob_client.download_blob()
                blob_content = BytesIO(download_stream.readall())

                # Upload the in-memory file-like object to Google Drive
                gfile = drive.CreateFile({'parents': [{'id': output_folder_id}], 'title': blob.name})
                gfile.content = blob_content
                gfile.Upload()

            # Show success message
            st.success("Image frames successfully shared to Google Drive")

# Download button functionality
if st.session_state.download_button == 1:
    # Create a temporary zip file
    with ZipFile("frames.zip", "w") as zip_file:
        # Get list of blobs in the container
        container_client = blob_service_client.get_container_client(container=container_name)
        blob_list = container_client.list_blobs()

        # Download and add each blob to the zip file
        for blob in blob_list:
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob.name)
            download_stream = blob_client.download_blob()
            blob_content = BytesIO(download_stream.readall())
            blob_content.seek(0)
            zip_file.writestr(blob.name, blob_content.getvalue())

    # Read the binary content of the zip file
    with open("frames.zip", "rb") as zip_file:
        zip_binary_content = zip_file.read()

    # Offer the zip file for download
    st.download_button("Download Frames", zip_binary_content, file_name="extracted_frames.zip", mime="application/zip")
    # Show success message
    # st.success("Image frames successfully downloaded")
