# 导入相关库，注意这里的zhipuai的版本必须是1.0.7，新版本的zhipuai运行此代码时会报错
from wxauto import WeChat
import zhipuai
import time

# 这个是预设提示词
PRESET_PROMPT = (
    "你是一个友善且轻松的微信群聊机器人，擅长用平和而又有趣的方式回应群友的问题。"
    "你的回答要简洁明了，但不失温暖，让大家感到轻松愉快。"
    "对简单问题，提供直接的答案，但不失亲切感。对复杂问题，先简要概括，再给出具体建议。"
    "偶尔可以用一些生活化的表达方式，增加互动感。"
    "遇到无聊或无意义的提问，机智地化解尴尬。\n"
    "例如：\n"
    "问：“今天晚上吃什么？”\n"
    "答：“这个问题真难，吃啥都行，只要有人请客就好。”\n"
    "问：“如何追到喜欢的人？”\n"
    "答：“首先，做自己；然后，真诚对待；最后，耐心等待。”\n"
    "问：“天气怎么样？”\n"
    "答：“天气不错，阳光明媚，适合出去走走。”\n"
    "问：“哈哈哈哈”\n"
    "答：“看来心情不错，今天有什么开心事？”"
)


def getText(role, content, text=[]):
    jsoncon1 = {}
    jsoncon1["role"] = "system"
    jsoncon1["content"] = PRESET_PROMPT
    text.append(jsoncon1)

    # role 是指定角色，content 是 prompt 内容
    jsoncon2 = {}
    jsoncon2["role"] = role
    jsoncon2["content"] = content
    text.append(jsoncon2)

    return text


def get_ai_reply(role, content):
    zhipuai.api_key = "这里填写你的api key"
    model = "这里写你选择的大模型版本"

    question = getText(role=role, content=content)
    # 请求模型
    response = zhipuai.model_api.invoke(model=model, prompt=question)
    return response["data"]["choices"][0]["content"]


# 获取微信窗口对象
wx = WeChat()

# 设置监听列表
listen_list = ["这里写群聊名称或者好友名称", "文件传输助手"]
# 循环添加监听对象
for i in listen_list:
    wx.AddListenChat(who=i, savepic=False)

# 持续监听消息
wait = 1  # 设置1秒查看一次是否有新消息
while True:
    msgs = wx.GetListenMessage()
    for chat in msgs:
        who = chat.who  # 获取聊天窗口名（人或群名）
        one_msgs = msgs.get(chat)  # 获取消息内容
        # ai回复
        for msg in one_msgs:
            msgtype = msg.type  # 获取消息类型
            content = msg.content  # 获取消息内容，字符串类型的消息内容
            print(f"【{who}】：{content}")

            if (
                msgtype == "friend" and "@wxBOT" in content
            ):  # 只有当好友/群成员发消息，而且消息包含“@wxBOT”的时候才回复
                reply = get_ai_reply(role="user", content=content)
                msg.quote(reply)  # 对消息进行引用回复
    time.sleep(wait)
