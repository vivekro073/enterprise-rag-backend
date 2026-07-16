from sqlalchemy import String, Column, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP
from database import Base
from sqlalchemy.sql.expression import text




class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    upload_date = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    pinecone_namespace = Column(String, nullable=False, unique=True)

class ChatMessages(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    uuid = Column(String, ForeignKey('documents.pinecone_namespace', ondelete="CASCADE"), nullable=False)

    document = relationship("Document", backref="chats")

