from openai import OpenAI


class LLMClient:
    def __init__(self):
        self.api_key = "sk-2505ce4643044eaab9a653a1f58752bb"
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.model_name = "qwen-plus"
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate_response(self, messages):
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"