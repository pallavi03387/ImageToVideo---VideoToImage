import streamlit as st
from azure.storage.blob import BlobServiceClient
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import cv2
import os
import numpy as np

# Azure Blob Storage Connection
# api_key = st.secrets["my_api_key"]
connect_str = st.secrets["connection_str"]
blob_service_client = BlobServiceClient.from_connection_string(connect_str)

# Function to create a container in Azure Blob Storage
def create_container(container_name):
    container_client = blob_service_client.get_container_client(container_name)
    print("container client: ",container_client)
    if not container_client.exists():
        container_client.create_container()
    else:
        blob_list = container_client.list_blobs()
        if blob_list:
            for blob in blob_list:
                container_client.get_blob_client(blob.name).delete_blob()
    return container_name

# Function to upload frames to Azure Blob Storage
def upload_frames_to_blob_storage(frame_folder, container_name):
    container_client = blob_service_client.get_container_client(container_name)
    for frame_file in os.listdir(frame_folder):
        frame_path = os.path.join(frame_folder, frame_file)
        blob_name = f"{container_name}/{frame_file}"
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        with open(frame_path, "rb") as frame_data:
            blob_client.upload_blob(frame_data, overwrite=True)

# Function to create a video from frames in Azure Blob Storage
def get_video_from_frames(container_name, output_video_name,frame_skip_rate):
    # Create a VideoCapture object
    frames = []
    # Access the container
    container_client = blob_service_client.get_container_client(container_name)
    blob_list = container_client.list_blobs()

    # Sort the blob list based on numerical part of filenames
    # sorted_blob_list = sorted(blob_list, key=lambda x: int(x.name.split(".")[0][5:]))

    # Retrieve frames from Azure Blob Storage
    for blob in blob_list:
        blob_client = container_client.get_blob_client(blob)
        download_stream = blob_client.download_blob()
        frame_bytes = download_stream.readall()

        # Decode frame from bytes
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        frames.append(frame)

    #video = cv2.VideoWriter(video_name,cv2.VideoWriter_fourcc(*'XVID'), 2, (width,height))
    # Write frames to a video file
    height, width, _ = frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_name, fourcc, frame_skip_rate, (width, height))

    for frame in frames:
        out.write(frame)

    # Release the VideoWriter object
    out.release()

    # Upload the video file to another container
    output_container_name = "video-container"
    output_blob_client = blob_service_client.get_blob_client(container=output_container_name, blob=output_video_name)
    with open(output_video_name, "rb") as data:
        output_blob_client.upload_blob(data.read(), overwrite=True)

    # Clean up local video file
    os.remove(output_video_name)


# Streamlit app setup
st.set_page_config(
    page_title="Frame to Video Conversion",
    page_icon="🎥",
    layout="wide")

# Frame uploader
st.header("Convert Frames to Video")
uploaded_frames = st.file_uploader("Upload multiple frames...", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

# Frame skip input
frame_skip = int(st.slider("Select Frame Rate", 1, 100, 5))

# Container name input
container_name = "temporary-frames"


# Convert frames to video button
convert_button = st.button("Convert Frames to Video", key="convert_button")
share_button1 = st.button("Share to Drive")
# download_button1 = st.button("Download the file", key="download_button")

if "download_button" not in st.session_state:
    st.session_state.download_button = 0

if "share_button" not in st.session_state:
    st.session_state.share_button = 0

# Convert frames to video and download
if convert_button and uploaded_frames:
    # Create Azure Blob Storage container
    create_container(container_name)
    # Upload frames to Azure Blob Storage
    for frame_file in uploaded_frames:
        frame_data = frame_file.read()
        frame_blob_name = f"{frame_file.name}"
        frame_blob_client = blob_service_client.get_blob_client(container=container_name, blob=frame_blob_name)
        frame_blob_client.upload_blob(frame_data, overwrite=True)
    
    # making the video
    get_video_from_frames(container_name, "converted-video.mp4",frame_skip)
    st.success("Video Successfully made")
    st.session_state.download_button = 1
    st.session_state.share_button = 1

if st.session_state.download_button == 1:
    container_name = "video-container"
    video_name = "converted-video.mp4"
    # download_path = "converted-video.mp4"
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=video_name)
    
    # Download the video file
    download_stream = blob_client.download_blob()
    video_content = download_stream.readall()
    st.download_button(label="Click to Download", data=video_content, file_name=video_name, mime="video/mp4")

if share_button1:
    if st.session_state.share_button == 1:
        container_name = "video-container"
        video_name = "converted-video.mp4"
        # download_path = "converted-video.mp4"
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=video_name)

        # Download the video file
        download_stream = blob_client.download_blob()
        video_content = download_stream.readall()

        with open(video_name, "wb") as video_file:
            video_file.write(video_content)

        # Authenticate with Google Drive
        gauth = GoogleAuth()
        drive = GoogleDrive(gauth)

        # Create a file in Google Drive
        drive_file = drive.CreateFile()
        drive_file.SetContentFile(video_name)  # Set the content from the downloaded video
        drive_file.Upload()
        st.success(f"Video successfully copied to Google Drive")