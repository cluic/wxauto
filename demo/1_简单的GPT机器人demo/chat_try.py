from llm import GPT
import os
import time
from dotenv import load_dotenv

# 读取相关环境变量
load_dotenv()

gpt = GPT(
    api_key = os.getenv('OPENAI_API_KEY'),
    base_url = os.getenv('OPENAI_BASE_URL'),
    prompt="你是一个智能助手，用于回复人们的各种问题"
)

reply = gpt.chat('HI!')

print(reply)