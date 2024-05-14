## 简介
这是一个利用oepnai的api实现的聊天机器人，可以生成聊天对话。

## 安装依赖
在安装了wxauto的情况下，只需要执行以下命令:
pip install openai

## openai_api_key的获取和设置
详见官方文档:https://platform.openai.com/docs

## 使用方法

### 1.开启代理
openai的api需要魔法访问

### 2.创建一个机器人
要创建一个机器人，需要如下几个参数
- human_group_info:包含如下选项：
    -- name: 群组/人名称
    -- condition: 触发对话时，对方信息必须含有的关键词（如群聊中出现了@自己）
    -- condition_type: 将对话输入给GPT时，是否需要过滤关键词，1为需要，0为不需要
    -- role_file: 角色配置路径
    -- pretrained_file: 预训练对话集路径
- client:oepnai的api client
- model:需要使用的GPT模型，查看官方文档获取模型名称

### 3.添加监听列表并获取所有未读消息
- 使用WeChat的AddListenChat方法，将所有机器人的聊天对象添加到监听列表中。
- 使用WeChat的GetListenMessage()方法获取所有聊天信对象和对应信息
- 详见根目录下的README.md文件。

### 4.启动机器人
使用机器人Robot的chat(msgs)方法，msgs为3中GetListenMessage()方法获取所有聊天信对象和对应信息，可对获取的msgs中的所有信息对相应对象进行回复

## 使用示例
详见gpt-chat下的demo.py文件
