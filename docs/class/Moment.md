---
weight: 5
bookFlatSection: true
title: "朋友圈类"
---

## MomentsWnd

**朋友圈窗口**对象，即的是朋友圈的窗口对象，提供对朋友圈窗口的各种操作，如获取朋友圈内容、刷新、关闭等功能。

```python
from wxauto import WeChat

wx = WeChat()
pyq = wx.Moments()   # 打开朋友圈并获取朋友圈窗口对象（如果为None则说明你没开启朋友圈，需要在手机端设置）
```

### GetMoments

**获取朋友圈内容**

```python
# 获取当前页面的朋友圈内容
moments = pyq.GetMoments()

# 通过`next_page`参数获取下一页的朋友圈内容
moments = pyq.GetMoments(next_page=True)
```

**参数**：

|   参数    | 类型 | 默认值  |                             说明                             |
| :-------: | :--: | :---: | :----------------------------------------------------------: |
| next_page | bool | False |                       是否翻页后再获取                       |
|  speed1   | int  |   3   |  翻页时的滚动速度，根据自己的情况进行调整，建议3-10自行调整  |
|  speed2   | int  |   1   | 翻页最后时的速度，避免翻页过多导致遗漏所以一般比speed1慢，建议1-3 |

**返回值**：List[[Moments](#Moments)]

### Refresh

**刷新朋友圈**

```python
pyq.Refresh()
```

### close

**关闭朋友圈**

```python
pyq.close()
```


## Moments

**朋友圈内容**对象，即的是朋友圈的内容对象，提供对朋友圈的各种操作，如获取朋友圈内容、点赞、评论等功能。

![Moments](/images/moment.png)

```python
# 获取朋友圈对象
moments = pyq.GetMoments()

# 获取第一条朋友圈
moment = moments[0]
```


### 获取朋友圈内容

```python
# 获取朋友圈内容
info = moment.info
# {
#     'type': 'moment',            # 类型，分为`朋友圈`和`广告`
#     'id': '4236572776458165',    # ID
#     'sender': '天天鲜花2号客服',   # 发送者
#     'content': '客订花束',        # 内容，就是朋友圈的文字内容，如果没有文字内容则为空字符串
#     'time': '4分钟前',            # 发送时间
#     'img_count': 3,              # 图片数量
#     'comments': [],              # 评论
#     'addr': '',                  # 发送位置
#     'likes': []                  # 点赞
# }

moment.sender
# '天天鲜花2号客服'

moment.content
# '客订花束'

moment.time
# '4分钟前'

# info中所有的键值对都可以通过对象的属性来获取，就不一一列举了
...
```

### SaveImages

**保存朋友圈图片**

**参数**：

|     参数     |    类型     | 默认值 |                             说明                             |
| :----------: | :---------: | :----: | :----------------------------------------------------------: |
| `save_index` | int \| list |  None  | 保存图片的索引，可以是一个整数或者一个列表，如果为None则保存所有图片 |
|  `savepath`  |     str     |  None  | 绝对路径，包括文件名和后缀，例如："D:/Images/微信图片_xxxxxx.jpg"，如果为None则保存到默认路径 |

**返回值**：List[str]，保存的图片的绝对路径列表

```python
# 获取朋友圈图片
images = moment.SaveImages()
# [
#     'D:/Images/微信图片_xxxxxx1.jpg',
#     'D:/Images/微信图片_xxxxxx2.jpg',
#     'D:/Images/微信图片_xxxxxx3.jpg',
#     ...
# ]
```

### Like

**点赞朋友圈**

**参数**：

| 参数 | 类型 | 默认值 | 说明 |
| :--: | :--: | :----: | :--: |
| like | bool |  True  | True点赞，False取消赞 |

```python
# 点赞
moment.Like()
# 取消赞
moment.Like(False)
```

**返回值**：无

### Comment

**评论朋友圈**

**参数**：

| 参数 | 类型   | 默认值 | 说明 |
| :--: | :----: | :----: | :--: |
| text | str |  必填  | 评论内容 |

```python
# 评论
moment.Comment('评论内容')
```

**返回值**：无