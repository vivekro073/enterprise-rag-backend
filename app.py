import streamlit as st
import requests
from aiohttp import payload

# 1. Page Configuration
st.set_page_config(page_title="PDF Analyzer", page_icon="📄")
st.title("RAG PDF Analyzer 🤖")

# 2. Initialize Session State
# This is how Streamlit remembers the UID and our chat history between button clicks
if "document_id" not in st.session_state:
    st.session_state.document_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. The Sidebar (Upload Phase)
with st.sidebar:
    st.header("1. Upload your PDF")
    uploaded_file = st.file_uploader("Choose a file", type="pdf")

    if st.button("Process Document"):
        if uploaded_file is not None:
            with st.spinner("Uploading and building vector space..."):
                # Package the file to send to FastAPI
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}

                try:
                    # Fire the POST request to your FastAPI backend
                    response = requests.post("http://127.0.0.1:8000/uploadfile/", files=files)

                    if response.status_code == 200:
                        data = response.json()
                        # THE INVISIBLE HANDOFF: Save the generated UUID to session state
                        st.session_state.document_id = data.get("document_id")
                        st.success("Success! Document processed.")
                    else:
                        st.error(f"Backend Error: {response.text}")
                except Exception as e:
                    st.error(f"Connection failed. Is your FastAPI server running? ({e})")
        else:
            st.warning("Please upload a PDF first.")

# 4. The Main Chat Interface (Visual Display)
# This loop draws all previous messages on the screen
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant" and "sources" in msg:
            with st.expander("View Source Chunks"):
                for i, chunk in enumerate(msg["sources"]):
                    st.markdown(f"**Chunk {i + 1}:**\n{chunk}")
                    st.divider()

# 5. The Input Box (Search Phase)
if prompt := st.chat_input("Ask a question about your document..."):

    # Immediately draw the user's question on the screen
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Make sure a document is actually uploaded before searching
    if not st.session_state.document_id:
        with st.chat_message("assistant"):
            st.warning("Please upload and process a PDF in the sidebar first!")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Construct the GET request URL with the hidden UUID
                url = f"http://127.0.0.1:8000/search/"
                payload = {"query": prompt, "uid": str(st.session_state.document_id)}

                try:
                    res = requests.post(url, json=payload)
                    if res.status_code == 200:
                        # FastAPI returns the LCEL string as JSON
                        answer_data = res.json()

                        # Extract the separate elements from the dictionary
                        text_answer = answer_data.get("answer", "")
                        source_chunks = answer_data.get("sources", [])

                        # 1. Draw the text answer onto the screen immediately
                        st.markdown(text_answer)

                        # 2. FIXED: Save ONLY the text string to history (not the whole dictionary)
                        st.session_state.messages.append({"role": "assistant",
                                                          "content": text_answer,
                                                          "sources": source_chunks})

                        # 3. FIXED: Display the sources cleanly using a loop inside the expander
                        if source_chunks:
                            with st.expander("View Source Chunks"):
                                for i, chunk in enumerate(source_chunks, 1):
                                    st.markdown(f"**Chunk {i}:**")
                                    st.write(chunk)
                                    if i < len(source_chunks):
                                        st.divider()
                    else:
                        st.error(f"Search failed: {res.text}")
                except Exception as e:
                    st.error(f"Could not connect to backend. ({e})")