import threading
from LLMClient import LLMClient


class Robot:
    def __init__(self, name, persona, wechat):
        self.name = name
        self.persona = persona
        self.wechat = wechat
        self.llm_client = LLMClient()
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def send_message_to_llm(self, message, nickname):
        if not self.running:
            return

        user_messages = [{"role": "system", "content": self.persona}, {"role": "user", "content": message}]

        reply = self.llm_client.generate_response(user_messages)
        # 在回复内容前面加上 @nickname
        reply_with_at = f"@{nickname} {reply}"
        self.wechat.SendMsg(reply_with_at, nickname)
        self.running = False

    def send_message_async(self, message, nickname):
        if not self.running:
            return

        thread = threading.Thread(target=self.send_message_to_llm, args=(message, nickname))
        thread.start()
