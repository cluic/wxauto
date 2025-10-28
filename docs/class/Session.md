---
weight: 4
bookFlatSection: true
title: "Session类"
---

## Session 类方法

```python
... # 此处省略wx对象的初始化

sessionbox = wx.SessionBox
```

### search

**仅用于触发搜索**，返回搜索结果，不会进行下一步的动作，可自行处理搜索结果

**示例**：

```python
search_result = sessionbox.search('张三')
for item in search_result:
    print(f"type: {item.type}, text: {item.text}")
```

**参数**：

|   参数    | 类型 | 默认值  |        说明             |
| :-------: | :--: | :---: | :-------------------: |
| keywords | str | False |  搜索关键词      |
| force | bool | False |  是否强制等待，避免未搜索到就返回结果      |
| force_wait | Union[float, int] | 0.5 |  强制等待时间，秒      |

**返回值**：

List[[SearchResultElement](#searchresultelement)]

### go_top

回到会话列表顶部

**参数**：无

**返回值**：无

### roll_up

向上滚动会话列表

**参数**：

|   参数    | 类型 | 默认值  |        说明             |
| :-------: | :--: | :---: | :-------------------: |
| n | int | 5 |  滚动次数，自行调节滚动幅度      |

**返回值**：无

### roll_down

向下滚动会话列表

**参数**：

|   参数    | 类型 | 默认值  |        说明             |
| :-------: | :--: | :---: | :-------------------: |
| n | int | 5 |  滚动次数，自行调节滚动幅度      |

**返回值**：无



## SessionElement

![SessionElement](/images/session_element.png)

| 属性     | 类型   | 描述（以上图为例）       |
| -------- | ------ | --------------- |
| name     | str    | 会话名（wxauto三群）  |
| time     | str    | 时间（2025-05-14 14:41）  |
| content     | str    | 消息内容（[10条]天道酬勤：这..）  |
| ismute     | bool    | 是否消息免打扰（True）  |
| isnew     | bool    | 是否有新消息（True）  |
| new_count     | int    | 新消息数量（10）  |
| info     | Dict[str, Any]    | 会话信息（包含了上述所有属性的dict）  |

```python
from wxauto import WeChat

wx = WeChat()
sessions = wx.GetSession()
session = sessions[0]  # 获取第一个会话
```

### click

**点击会话**，即切换到这个聊天窗口

参数：无

返回值：无

示例：
```python
session.click()
```

### double_click

**双击会话**，即将这个聊天窗口独立出去

参数：无

返回值：无

示例：
```python
session.double_click()
```

### delete

**删除会话**

参数：无

返回值：[`WxResponse`](/docs/class/other/#wxresponse)

示例：
```python
session.delete()
```

### hide

**隐藏会话**

参数：无

返回值：[`WxResponse`](/docs/class/other/#wxresponse)

示例：
```python
session.hide()
```

### select_option

**选择会话选项**，即右键点击会话，然后选择某个选项

参数：

| 参数名 | 类型 | 说明 |
| :--- | :--- | :--- |
| option | str | 选项名称，例如“置顶”、“标为未读”等 |

返回值：[`WxResponse`](/docs/class/other/#wxresponse)

## SearchResultElement

会话搜索结果对象

| 属性     | 类型   | 描述             |
| -------- | ------ | ---------------- |
| type  | str    | 搜索结果对象的UI类型，一般`pane`是分割线或者标签，不可交互；`listitem`是搜索结果，可交互  |
| text  | str    | 搜索结果，有时候卡可能为空，建议使用`get_all_text`方法进行完整判断  |

### get_all_text

获取该结果对象的所有UI文字内容，用于判断是不是你要的搜索结果

**参数**：无

**返回值**：List[str]

### click

点击该搜索对象

**参数**：无

**返回值**：无

### close

关闭搜索窗口，关闭后本次搜索的所有对象均不可再交互

**参数**：无

**返回值**：无