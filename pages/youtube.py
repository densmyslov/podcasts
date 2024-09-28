import streamlit as st
import boto3
import json
import io
import os
import re
from time import sleep, time
import Home as pod
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
import threading
from pytubefix import YouTube
from pytubefix.cli import on_progress
from dotenv import load_dotenv
load_dotenv()

# PASSWORD = pod.PASSWORD

# if 'password' not in st.session_state:
#     st.session_state.password = ''

# if PASSWORD != st.session_state.password:
#     st.error("Please enter your password at Home page")
#     st.stop()
# else:


S3_CLIENT = pod.s3_client



# def upload_to_s3(file_buffer, bucket_name, s3_filename):

#     S3_CLIENT.upload_fileobj(file_buffer, bucket_name, s3_filename)

st.title("Transcribe Video/Audio files")

UPLOAD_FOLDER = pod.FOLDER

uploaded_file = None
file_name = None
#-----------------------------DRAG AND DROP------------------------------------

def replace_dots_except_last(input_string):
    # Replace dots with a lookahead to ensure it's not the last dot
    input_string =  re.sub(r'\.(?=.*\.)', '', input_string)
    return re.sub("[,-/:|? ]","_", input_string)

# Function to upload file to S3 with progress tracking
def upload_to_s3(s3_client, file_buffer, bucket_name, s3_filename, progress_tracker):
    
    file_size = os.path.getsize(file_buffer.name)
    chunk_size = 5 * 1024 * 1024  # 5 MB
    progress = 0

    file_buffer.seek(0)  # Ensure we're at the start of the file

    try:
        # Initialize multipart upload
        multipart_upload = s3_client.create_multipart_upload(Bucket=bucket_name, Key=s3_filename)
        parts = []
        part_number = 1

        while True:
            chunk = file_buffer.read(chunk_size)
            if not chunk:
                break
            response = s3_client.upload_part(
                Bucket=bucket_name, 
                Key=s3_filename, 
                PartNumber=part_number, 
                UploadId=multipart_upload['UploadId'], 
                Body=chunk
            )
            parts.append({
                'PartNumber': part_number,
                'ETag': response['ETag']
            })
            progress += len(chunk)
            progress_tracker['progress'] = progress / file_size * 100
            part_number += 1
            sleep(0.1)  # simulate delay for demonstration

        # Complete multipart upload
        s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=s3_filename,
            UploadId=multipart_upload['UploadId'],
            MultipartUpload={'Parts': parts}
        )
        progress_tracker['success'] = True
    except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
        progress_tracker['success'] = False
        progress_tracker['error'] = str(e)
        try:
            s3_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=s3_filename,
                UploadId=multipart_upload['UploadId']
            )
        except Exception as abort_error:
            progress_tracker['abort_error'] = str(abort_error)
    except Exception as e:
        progress_tracker['success'] = False
        progress_tracker['error'] = str(e)
        try:
            s3_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=s3_filename,
                UploadId=multipart_upload['UploadId']
            )
        except Exception as abort_error:
            progress_tracker['abort_error'] = str(abort_error)


uploaded_file = st.file_uploader("Select mp3 file from local disk", type=['mp3'])

if uploaded_file is not None:
    st.success(f"Loaded file from disk to memory: {uploaded_file.name}")
    st.info("Click the button below to upload the file to S3.")

    if st.button(":red[Upload file to S3]"):
        file_buffer = io.BytesIO(uploaded_file.read())
        BUCKET_NAME = "hamazin-podcasts"
        UPLOAD_FOLDER = "lex-fridman"  # define your upload folder
        S3_FILENAME = f"{UPLOAD_FOLDER}/{uploaded_file.name}/from_local.mp4"

        progress_tracker = {'progress': 0, 'success': None, 'error': None, 'abort_error': None}

        progress_bar = st.progress(0)
        status_text = st.empty()

        # Start upload in a separate thread
        upload_thread = threading.Thread(
            target=upload_to_s3,
            args=(S3_CLIENT, file_buffer, BUCKET_NAME, S3_FILENAME, progress_tracker)
        )
        upload_thread.start()

        # Update progress in main thread
        while upload_thread.is_alive():
            progress_bar.progress(int(progress_tracker['progress']))
            status_text.text(f"Uploading... {progress_tracker['progress']:.2f}%")
            sleep(0.1)

        upload_thread.join()

        if progress_tracker['success']:
            st.success(f"Uploaded {S3_FILENAME} to {BUCKET_NAME}!")
            progress_tracker = {'progress': 0, 'success': None, 'error': None, 'abort_error': None}
        else:
            st.error(f"Failed to upload file. Error: {progress_tracker['error']}")
            if progress_tracker['abort_error']:
                st.error(f"Failed to abort multipart upload. Error: {progress_tracker['abort_error']}")

            
#-----------------------------PASTE YOUTUBE URL------------------------------------

# Streamlit app starts here
video_url = st.text_input("Paste URL of a YouTube video here")
if len(video_url) > 0 and 'youtu' in video_url:

    s = time()
    yt = YouTube(video_url, on_progress_callback = on_progress)
    print(yt.title)
    
    ys = yt.streams.get_audio_only()
    file_name = ys.download(mp3=True)
    
    # Get the audio stream
    # ys = yt.streams.filter(only_audio=True).first()
    
    # # Download the audio stream and save it as an MP3 file
    # file_name = ys.download()

    
    st.write('Downloaded file:', file_name)
    e = time()
    st.write(f"Download took {e-s:.2f} seconds")

    file_title = yt.title
    video_id = yt.video_id
    file_length = yt.length
    author = yt.author
    description = yt.description
    rating = yt.rating
    file_size = os.path.getsize(file_name) / (1024 * 1024)
    st.write(f"File size, Mb: {file_size:.2f}")

    # Prepare to upload to S3
    file_buffer = open(file_name, 'rb')
    BUCKET_NAME = "hamazin-podcasts"
    UPLOAD_FOLDER = "lex-fridman"  # Define your upload folder
    s3_filename = replace_dots_except_last(file_title)

    # You can add your upload to S3 logic here
    # Example:
    # s3_client.upload_fileobj(file_buffer, BUCKET_NAME, f"{UPLOAD_FOLDER}/{s3_filename}")

    st.success(f"Saved {file_title} to S3 as {UPLOAD_FOLDER}/{s3_filename}")



    #===========================UPLOAD MP3 FILE===============================
    S3_FILENAME = f"{UPLOAD_FOLDER}/{s3_filename}_{video_id}/from_local.mp4"

    progress_tracker = {'progress': 0, 'success': None, 'error': None, 'abort_error': None}

    progress_bar = st.progress(0)
    status_text = st.empty()

    # Start upload in a separate thread
    upload_thread = threading.Thread(
        target=upload_to_s3,
        args=(S3_CLIENT, file_buffer, BUCKET_NAME, S3_FILENAME, progress_tracker)
    )
    upload_thread.start()

    # Update progress in main thread
    while upload_thread.is_alive():
        progress_bar.progress(int(progress_tracker['progress']))
        status_text.text(f"Uploading to s3 bucket, do not close your browser {progress_tracker['progress']:.2f}%")
        sleep(0.1)

    upload_thread.join()

    if progress_tracker['success']:
        st.success(f"Uploaded {S3_FILENAME} to {BUCKET_NAME}!")
        progress_tracker = {'progress': 0, 'success': None, 'error': None, 'abort_error': None}
    else:
        st.error(f"Failed to upload file. Error: {progress_tracker['error']}")
        if progress_tracker['abort_error']:
            st.error(f"Failed to abort multipart upload. Error: {progress_tracker['abort_error']}")
    
    file_buffer.close()

#======================UPLOAD MP3 METADATA FILE=====================
    key = f"{UPLOAD_FOLDER}/{s3_filename}_{video_id}/mp4_file_data.json"
    BUCKET_NAME = "hamazin-podcasts"
    message = {"youtube_url": video_url,
            "bucket_name": BUCKET_NAME,
            "folder_name": UPLOAD_FOLDER,
            "s3_filename": s3_filename,
            "file_title":file_title,
            "video_id":video_id,
            "file_length":file_length,
            "author":author,
            "description":description,
            "rating":rating,
            "file_size":file_size
            }
    S3_CLIENT.put_object(Bucket=BUCKET_NAME, Key=key, Body=json.dumps(message))




