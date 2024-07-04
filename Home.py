import streamlit as st
import os
import boto3
from dotenv import load_dotenv
load_dotenv()


PASSWORD = st.secrets["PASSWORD"]
FOLDER = st.secrets["FOLDER"]
S3_BUCKET = st.secrets["S3_BUCKET"]
AWS_ACCESS_KEY = st.secrets["AWS_ACCESS_KEY"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
MILVUS_CLUSTER_ID = st.secrets["MILVUS_CLUSTER_ID"]
MILVUS_API_KEY = st.secrets["MILVUS_API_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]


s3_client = boto3.client('s3',
                         aws_access_key_id = AWS_ACCESS_KEY,
                        aws_secret_access_key = AWS_SECRET_ACCESS_KEY)

# if 'password' not in st.session_state:
#     st.session_state.password = ''
# st.session_state.password = st.text_input("password", 
#                         type='password')
# if st.session_state.password == PASSWORD:
#     st.success("Correct password")
# else:
#     st.error("Please enter password")

st.video('https://youtu.be/KFHXJp2Lehs')


pages = {
    "Youtube link": "./pages/youtube",
    "Podcast Q&A": "./pages/rag"
}