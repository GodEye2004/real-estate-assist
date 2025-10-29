from rdflib.tools.csv2rdf import column
from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from traits.trait_types import false

Base = declarative_base()

class TenatData(Base):
    __tablename__ = "ai_assist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=false)
    category = Column(String, nullable=false)
    data = Column(JSON, nullable=False)
