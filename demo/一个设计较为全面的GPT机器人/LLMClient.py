from openai import OpenAI


class LLMClient:
    def __init__(self):
        self.api_key = "your_api_key"
        self.base_url = "your_model_url"
        self.model_name = "model_name"
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
