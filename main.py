import os
from fastapi import FastAPI
import uvicorn
from database import engine
import models
from pydantic import BaseModel
from datetime import datetime
from fastapi import UploadFile, Depends, HTTPException
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from database import get_db
from sqlalchemy.orm import Session
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from operator import itemgetter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import uuid
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

class Document(BaseModel):
    id: int
    filename: str
    upload_date: datetime
    pinecone_namespace: str

class SearchRequest(BaseModel):
    query: str
    uid: str

class PostgreSQLChatHistory(BaseChatMessageHistory):

    def __init__(self, session_id, db):
        self.session_id = session_id
        self.db = db

    @property
    def messages(self) -> list[BaseMessage]:
        post_query = self.db.query(models.ChatMessages).filter(models.ChatMessages.uuid == self.session_id)
        history_timeline = []
        for post in post_query:
            if post.role == "assistant":
                msg = AIMessage(content=post.content)
                history_timeline.append(msg)
            elif post.role == "user":
                msg = HumanMessage(content=post.content)
                history_timeline.append(msg)
        return history_timeline

    def add_message(self, message: BaseMessage) -> None:
        role = ""
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"

        new_msg = models.ChatMessages(role=role, content=message.content, uuid=self.session_id)
        self.db.add(new_msg)
        self.db.commit()
        self.db.refresh(new_msg)

    def clear(self) -> None:
        clear_msg = self.db.query(models.ChatMessages).filter(models.ChatMessages.uuid == self.session_id)
        clear_msg.delete()
        self.db.commit()





@app.get("/")
def home():
    return {"Hello": "World"}

# Creates a upload directory if needed for finding the file.
UPLOADED_FILES_DIR = "upload"
os.makedirs(UPLOADED_FILES_DIR, exist_ok=True)

@app.post("/uploadfile/")
def upload_file(file: UploadFile, db: Session = Depends(get_db)):
    uid = str(uuid.uuid4())

    try:
        file_path = os.path.join(UPLOADED_FILES_DIR, file.filename)

        # Opens the PDF file and reads it.
        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)

        loader = PyPDFLoader(file_path=file_path)
        document = loader.load()

        # splitting the texts
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(document)

        # Embedding with Pinecone
        embedding = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", output_dimensionality=1536)
        PineconeVectorStore.from_documents(texts, embedding, index_name=os.environ["INDEX_NAME"], namespace=uid)

        new_doc = models.Document(
            filename = file.filename,
            pinecone_namespace= uid,
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    # Change your return statement to this:
    return {
        "message": "File processed successfully",
        "filename": file.filename,
        "document_id": new_doc.pinecone_namespace
    }

@app.post("/search/")
def search(request: SearchRequest, db: Session = Depends(get_db)):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", output_dimensionality=1536)
    llm = ChatGroq(temperature=0, model_name="openai/gpt-oss-120b")

    vectorstore = PineconeVectorStore(index_name=os.environ["INDEX_NAME"], embedding=embeddings, namespace=request.uid)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "Answer the question based on the following context:\n{context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "Question: {question}\n\nProvide a summarised answer in one paragraph:")
    ])

    def formated_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    retrieval_chain = (
                    RunnablePassthrough.assign(
                        context=itemgetter("question") | retriever | formated_docs
                    )
                    | prompt_template
                    | llm
                    | StrOutputParser()
            )
    raw_data = retriever.invoke(request.query)

    wrapped_chain = RunnableWithMessageHistory(
        runnable=retrieval_chain,
        get_session_history=lambda session_id: PostgreSQLChatHistory(session_id=session_id, db=db),
        input_messages_key="question",
        history_messages_key="chat_history",
    )

    result = wrapped_chain.invoke(
        {"question": request.query},
        config={"configurable": {"session_id": request.uid}}
    )

    return {"answer": result,
            "sources": [doc.page_content for doc in raw_data]}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)