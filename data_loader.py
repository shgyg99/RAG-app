from openai import OpenAI
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")

client_kwargs = {"api_key": API_KEY} if API_KEY else None
if client_kwargs and API_URL:
    client_kwargs["base_url"] = API_URL

client = OpenAI(**client_kwargs) if client_kwargs else None
