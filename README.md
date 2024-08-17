# Youtube podcasts: Speech-to-text and RAG
[link to demo app](https://podcasts-agent.streamlit.app)
### Paste url of a Youtube video with speech, for example a podcast, and get transcription and RAG.
* Speech-to-text model: Deepgram Nova-2
* Vector embedding model: 'text-embedding-3-small'; dim = 1536
* Vector Database: Milvus
* LLM: Openai GPT-4o
* Backend: AWS State Machine which orquestrates several lambda functions
* Frontend: Streamlit

<!-- ![Step functions graph](https://github.com/aguille-vert/podcasts/blob/main/step_functions_graph.png) -->

<p align="center">
    <a href="https://github.com/aguille-vert/podcasts/blob/main/step_functions_graph.png" target="_blank">
        <img src="https://github.com/aguille-vert/podcasts/blob/main/step_functions_graph.png" alt="Step functions graph" width="100"/>
    </a>
</p>
