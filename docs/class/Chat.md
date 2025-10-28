---
weight: 1
bookFlatSection: true
title: "Chat类"
---
## Chat 类属性

在了解`Chat`类的方法之前，我想先介绍一下为什么要做这个类。
`wxauto(x)`这个项目的原理是模拟人工对微信客户端的操作，拿取到的所有信息都是人眼可见的部分，
所以当我们想监听某个人或群消息的时候，需要把这个人的聊天窗口独立出来，以确保UI元素不会因为微信主窗口切换聊天而丢失，
同时也不需要每来一条信息都切换聊天窗口去获取。
所以，`Chat`类就是用来创建一个独立的聊天窗口，并获取这个聊天窗口的信息。

| 属性     | 类型   | 描述             |
| -------- | ------ | ---------------- |
| who  | str    | 当前子窗口的聊天对象名  |
| chat_type  | str    | 聊天窗口类型  |

### 聊天窗口类型 chat_type

获取当前聊天窗口的类型，返回值为字符串，取值范围如下：

- friend：好友
- group：群聊
- service：客服
- official：公众号

```python
chat_type = chat.chat_type
```


## Chat 类方法

### 显示窗口 Show

```python
chat.Show()
```

### 获取聊天窗口信息 ChatInfo

```python
info = chat.ChatInfo()
```

**返回值**：

- 类型：`dict`
- 描述：聊天窗口信息
- 返回值示例：
```python
# 好友
{'chat_type': 'friend', 'chat_name': '张三'}  

# 群聊
{'group_member_count': 500, 'chat_type': 'group', 'chat_name': '工作群'}  

# 客服
{'company': '@肯德基', 'chat_type': 'service', 'chat_name': '店长xxx'} 

# 公众号
{'chat_type': 'official', 'chat_name': '肯德基'} 
```

### @所有人 AtAll

```python
group = '工作群'
content = """
通知：
下午xxxx
xxxx
"""

wx.AtAll(content, group)
```

msg (str): 发送的消息

​      who (str, optional): 发送给谁. Defaults to None.

​      exact (bool, optional): 是否精确匹配. Defaults to False.

**参数**：

| 参数  | 类型   | 默认值 | 描述                                                         |
| ----- | ------ | ------ | ------------------------------------------------------------ |
| msg   | str    | None   | 发送的消息                                                   |
| who   | str    | None   | 发送给谁                                                     |
| exact | bool   | False  | 是否精确匹配                                                 |

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)
- 描述：是否发送成功


### 发送消息 SendMsg

```python
wx.SendMsg(msg="你好", who="张三", clear=True, at="李四", exact=False)
```

**参数**：

| 参数  | 类型                  | 默认值 | 描述                                                         |
| ----- | --------------------- | ------ | ------------------------------------------------------------ |
| msg   | str                   | 必填   | 消息内容                                                     |
| who   | str                   | None   | 发送对象，不指定则发送给当前聊天对象，**当子窗口时，该参数无效** |
| clear | bool                  | True   | 发送后是否清空编辑框                                         |
| at    | Union[str, List[str]] | None   | @对象，不指定则不@任何人                                     |
| exact | bool                  | False  | 搜索who好友时是否精确匹配，**当子窗口时，该参数无效**        |

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)
- 描述：是否发送成功

### 发送文本消息（打字机模式）SendTypingText

```python
wx.SendTypingText(msg="你好", who="张三", clear=True, exact=False)
```

**参数**：

| 参数  | 类型 | 默认值 | 描述                                                         |
| ----- | ---- | ------ | ------------------------------------------------------------ |
| msg   | str  | 必填   | 要发送的文本消息                                             |
| who   | str  | None   | 发送对象，不指定则发送给当前聊天对象，**当子窗口时，该参数无效** |
| clear | bool | True   | 是否清除原本的内容                                           |
| exact | bool | False  | 搜索who好友时是否精确匹配，**当子窗口时，该参数无效**        |

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)
- 描述：是否发送成功

**示例**：

```python
# 换行及@功能
wx.SendTypingText('各位下午好\n{@张三}负责xxx\n{@李四}负责xxxx', who='工作群')
```

### 发送文件 SendFiles

```python
wx.SendFiles(filepath="C:/文件.txt", who="张三", exact=False)
```

**参数**：

| 参数     | 类型      | 默认值 | 描述                                                         |
| -------- | --------- | ------ | ------------------------------------------------------------ |
| filepath | str\|list | 必填   | 要复制文件的绝对路径                                         |
| who      | str       | None   | 发送对象，不指定则发送给当前聊天对象，**当子窗口时，该参数无效** |
| exact    | bool      | False  | 搜索who好友时是否精确匹配，**当子窗口时，该参数无效**        |

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)
- 描述：是否发送成功

### 发送自定义表情 SendEmotion

```python
wx.SendEmotion(emotion_index=0, who="张三", exact=False)
```

**参数**：

| 参数          | 类型 | 默认值 | 描述                                                         |
| ------------- | ---- | ------ | ------------------------------------------------------------ |
| emotion_index | str  | 必填   | 表情索引，从0开始                                            |
| who           | str  | None   | 发送对象，不指定则发送给当前聊天对象，**当子窗口时，该参数无效** |
| exact         | bool | False  | 搜索who好友时是否精确匹配，**当子窗口时，该参数无效**        |

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)
- 描述：是否发送成功

### 获取当前聊天窗口的所有消息 GetAllMessage

```python
messages = wx.GetAllMessage()
```

**返回值**：

- 类型：List[[Message](#message-类方法)]
- 描述：当前聊天窗口的所有消息

### 加载当前窗口更多聊天记录 LoadMoreMessage

```python
wx.LoadMoreMessage()
```

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)
- 描述：是否发送成功

### 添加群成员 AddGroupMembers

```python
wx.AddGroupMembers(group="技术交流群", members=["张三", "李四"], reason="交流技术")
```

**参数**：

| 参数    | 类型                  | 默认值 | 描述                                             |
| ------- | --------------------- | ------ | ------------------------------------------------ |
| group   | str                   | None   | 群名                                             |
| members | Union[str, List[str]] | None   | 成员名或成员名列表                               |
| reason  | str                   | None   | 申请理由，当群主开启验证时需要，不填写则取消申请 |

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)
- 描述：是否添加成功

### 获取当前聊天群成员 GetGroupMembers

```python
members = wx.GetGroupMembers()
```

**返回值**：

- 类型：`List[str]`
- 描述：当前聊天群成员列表

### 移除群成员 RemoveGroupMembers

```python
wx.RemoveGroupMembers(group="群名", members=["成员名1", "成员名2"])
```

**参数**：

| 参数    | 类型    | 默认值 | 描述    |
| ------- | ------- | ------ | ------- |
| group   | str     | None   | 群名    |
| members | str     | None   | 成员名  |

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)
- 描述：是否移除成功

### 从群聊中添加好友 AddFriendFromGroup

```python
index = 5  # 申请群里索引值为5的成员为好友
remark = "备注名"
tags = ["标签1", "标签2"]
result = wx.AddFriendFromGroup(index=index, remark=remark, tags=tags)
if result:
    print("成功发起申请")
else:
    print(f"申请失败：{result['message']}")
```

**参数**：

| 参数    | 类型    | 默认值 | 描述    |
| ------- | ------- | ------ | ------- |
| index   | int     | None   | 群聊索引 |
| who     | str     | None   | 群名，当`Chat`对象时该参数无效，仅`WeChat`对象有效 |
| addmsg  | str     | None   | 申请理由，当群主开启验证时需要，不填写则取消申请 |
| remark  | str     | None   | 添加好友后的备注名 |
| tags    | list    | None   | 添加好友后的标签 |
| permission | Literal['朋友圈', '仅聊天'] | '仅聊天' | 添加好友后的权限 |
| exact   | bool    | False  | 是否精确匹配群聊名 |

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)

### 修改好友备注名或标签 ManageFriend

```python
wx.ManageFriend(remark="新备注名")
wx.ManageFriend(tags=["标签1", "标签2"])
```

**参数**：

| 参数   | 类型    | 默认值 | 描述     |
| ------ | ------- | ------ | -------- |
| remark | str     | None   | 备注名   |
| tags   | List[str] | None   | 标签列表 |

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)
- 描述：是否成功修改备注名或标签

### 管理当前群聊 ManageGroup

```python
wx.ManageGroup(name="新群名")
wx.ManageGroup(remark="新备注名")
wx.ManageGroup(myname="新群昵称")
wx.ManageGroup(notice="新群公告")
wx.ManageGroup(quit=True)   # 谨慎使用
```

**参数**：

| 参数   | 类型    | 默认值 | 描述     |
| ------ | ------- | ------ | -------- |
| name   | str     | None   | 群名称   |
| remark | str     | None   | 备注名   |
| myname | str     | None   | 我的群昵称 |
| notice | str     | None   | 群公告   |
| quit   | bool    | False  | 是否退出群，当该项为True时，其他参数无效 |

### 关闭窗口 Close

```python
wx.Close()
```

### 合并转发消息 MergeForward

**参数**：

| 参数   | 类型    | 默认值 | 描述     |
| ------ | ------- | ------ | -------- |
| targets   | Union[List[str], str]     | None   | 要转发的对象  |

**返回值**：

- 类型：[`WxResponse`](/docs/class/other/#wxresponse)
- 描述：是否成功转发
  
### 获取对话框 GetDialog

```python
if dialog := wx.GetDialog():
    dialog.click_button("确定")
```

**参数**：

| 参数   | 类型    | 默认值 | 描述     |
| ------ | ------- | ------ | -------- |
| wait   | int     | 3   | 隐性等待时间  |

**返回值**：

- 类型：[`WeChatDialog`](/docs/class/other/#wechatdialog)
- 描述：对话框对象，如果不存在则返回None

### 移除置顶消息 GetTopMessage

```python
if top_messages := wx.GetTopMessage():
    for top_message in top_messages:
        print(f"移除置顶消息: {top_message.content}")
        top_message.remove()
```

**参数**：无

**返回值**：

- 类型：`List[TopMsg]`