import streamlit as st
import json

import os
from dotenv import load_dotenv
from pymilvus import MilvusClient
from openai import OpenAI
from streamlit.connections import BaseConnection
from streamlit.runtime.caching import cache_data
import pandas as pd
import numpy as np
import boto3
from io import BytesIO
import Home as pod


load_dotenv()

OPENAI_API_KEY = pod.OPENAI_API_KEY
MILVUS_API_KEY = pod.MILVUS_API_KEY
MILVUS_CLUSTER_ID = pod.MILVUS_CLUSTER_ID
AWS_ACCESS_KEY = pod.AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY = pod.AWS_SECRET_ACCESS_KEY
S3_BUCKET = pod.S3_BUCKET
FOLDER = pod.FOLDER
PASSWORD = pod.PASSWORD

if PASSWORD != st.session_state.password:
    st.error("Please enter your password at Home page")
    st.stop()
else:

    s3_client = pod.s3_client


    @cache_data
    def get_all_videos_index_df():
        try:
            key = f'{FOLDER}/all_videos_index.df'
            obj = s3_client.get_object(Bucket=S3_BUCKET, Key = key)
            buffer = BytesIO(obj['Body'].read())
            return pd.read_parquet(buffer).drop_duplicates(subset=['file_name','segment_id'])
        except:
            st.write("There's no videos in your folder")
            return pd.DataFrame()

    def process_milvus_vectors(milvus_r):

        rag_df = pd.DataFrame(milvus_r[0])
        rag_df['file_name'] = rag_df['entity'].apply(lambda x: x['file_name'])
        rag_df['segment_id'] = rag_df['entity'].apply(lambda x: x['segment_id'])
        rag_df.pop('id')
        rag_df.pop('entity')
        rag_counts_df = pd.DataFrame(rag_df['segment_id'].value_counts()).reset_index()
        rag_counts_df.columns=['segment_id','count']
        rag_df_mean = rag_df.groupby('segment_id').agg({'distance':'mean'}).reset_index()
        rag_df_mean.columns = ['segment_id','dist']
        rag_df = rag_counts_df.merge(rag_df_mean).sort_values('dist').reset_index(drop=True)
        # Normalize the columns
        rag_df['normalized_count'] = (rag_df['count'] - rag_df['count'].min()) / (rag_df['count'].max() - rag_df['count'].min())
        rag_df['normalized_dist'] = (rag_df['dist'] - rag_df['dist'].min()) / (rag_df['dist'].max() - rag_df['dist'].min())
        # Calculate the score
        w1 = 0.5  # Weight for count
        w2 = 0.5  # Weight for dist (inverted)
        rag_df['score'] = w1 * rag_df['normalized_count'] + w2 * (1 - rag_df['normalized_dist'])

        median_score = rag_df['score'].median()
        # rag_df = rag_df.query("dist<=@median_dist & count>=2").sort_values('score',ignore_index=True)
        top_20_pc_num = int(np.ceil(len(all_videos_index_df)*0.2))
        rag_df= rag_df.query("score>=@median_score").sort_values('score',ascending = False).iloc[:top_20_pc_num,:]

        return rag_df

    all_videos_index_df = get_all_videos_index_df()
    if not all_videos_index_df.empty:
        file_names = all_videos_index_df['file_name'].unique()
        file_names = list(set(file_names))
        file_names.sort()
    else:
        file_names = []



    milvus_uri=f"https://{MILVUS_CLUSTER_ID}.api.gcp-us-west1.zillizcloud.com"


    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    # Set a default model
    if "openai_chat_model" not in st.session_state:
        st.session_state["openai_chat_model"] = "gpt-4o"

    if "openai_embed_model" not in st.session_state:
        st.session_state['openai_embed_model'] = "text-embedding-3-small"

    milvus_client = MilvusClient(
                                uri=milvus_uri,
                                token=MILVUS_API_KEY
                                )

    milvus_collection_name = 'podcasts'
    # st.write(milvus_client.describe_collection(collection_name="podcasts"))

    st.title("Chat About Your Video Podcast")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if st.sidebar.button(":red[Refresh page]"):
        st.session_state.messages = []
        st.cache_data.clear()

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    video_name = st.sidebar.selectbox("Select video", index = 0,options = file_names)


    if video_name:
        video_index_df = all_videos_index_df.query("file_name==@video_name").reset_index(drop=True).copy()
        st.dataframe(video_index_df)

        # Accept user input
        if Q := st.chat_input("What is up?"):
            st.write(Q)
            openai_r = openai_client.embeddings.create(
                                                        model="text-embedding-3-small",
                                                        input=Q,
                                                        encoding_format="float"
                                                        )

            # Access the embedding data
            if hasattr(openai_r, 'data') and openai_r.data:
                embedding = openai_r.data[0].embedding
                # st.write("embedding created")
                Vq = np.array(embedding).astype('float32')
                Vq = Vq.tolist()
                null_elements = [i for i in Vq if not i]

                # st.write(Vq[:5])
            else:
                st.write("Embedding could not be retrieved.")
            # Vq = openai_r['data'][0]['embedding']


            milvus_r = milvus_client.search(
                                            milvus_collection_name,
                                            data = [Vq],
                                            limit = 25,
                                            output_fields = ['segment_id','file_name']
                                            )
        # st.write(milvus_r[0])



            
            
            
        
            rag_df = process_milvus_vectors(milvus_r)
            
            st.dataframe(rag_df)

            segment_ids = rag_df['segment_id'].tolist()

            segment_texts = video_index_df.query("segment_id==@segment_ids")[['segment_id','text']].to_dict(orient='records')
            segment_texts = json.dumps(segment_texts)
            prompt = f"""Please analyze the Dialogue text and asnwer the Question below. In your answer make a reference 
            to the segment_ids on which you answer is based and corresponding text quotes. Output JSON.
            ### Example:
            {{
                "segment 1": {{"quote": "...",
                            "assistant_comment": "..."}},

                "segment 20" : {{"quote": "...",
                            "assistant_comment": "..."}}
                            }}
            ## Question: {Q}
            ## Dialogue Text : {segment_texts}

            """

            r_openai = openai_client.chat.completions.create(
                                                model="gpt-4o",
                                                messages=[
                                                    {"role": "system", "content": "You are a helpful assistant."},
                                                    {"role": "user", "content": prompt}
                                                ],
                                                response_format = {"type":"json_object"}
                                                            )
            completion = json.loads(r_openai.json())
            st.write(completion)

