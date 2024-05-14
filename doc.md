# wxauto调用文档（适用微信版本v3.9.8.15）


## 一、版本对比

本项目目前默认分支为**微信3.9.8.15**版本，使用前请先检查自己电脑微信是否为该版本，版本不同可能由于UI问题导致某些功能无法正常调用

> 注：如果你的微信版本可以用的话，也不需要过多纠结这个

![版本信息](https://github.com/cluic/wxauto/blob/WeChat3.9.8/utils/version.png)

## 二、获取wxauto

### 1. 使用git获取wxauto项目包

```shell
git clone https://github.com/cluic/wxauto.git
```

打开获取到的项目包文件夹，得到以下文件：

|      文件名      |  类型  |            描述            |
| :--------------: | :----: | :------------------------: |
|      utils       | 文件夹 | 深入研究用到的小工具及图片 |
|      wxauto      | 文件夹 |        主项目文件夹        |
|     demo.py      |  文件  |       简单的使用示例       |
|     LICENSE      |  文件  |        license文件         |
| requirements.txt |  文件  |      第三方依赖库文件      |

### 2. 安装依赖

```shell
pip install -r requirements.txt
```

等待安装完成即可

### 3. 测试运行

打开cmd，运行demo.py：

```shell
python demo.py
```

如果自动发送并打印了当前页面的聊天记录出来，并且最后输出“wxauto测试完成！”，则测试完成，可以继续调用wxauto来完成您的项目，如果报错，则欢迎发起Issues提问，如发现bug或者有更好的修改建议，也欢迎pull requests

## 三、使用文档

假设您已经完成了上面的测试，可以正常运行wxauto脚本

```python
# 导入
>>> from wxauto import WeChat

# 获取微信窗口对象
>>> wx = WeChat()
初始化成功，获取到已登录窗口：xxxx
```

上面定义了wx变量，下述文档不再重复定义和解释wx变量

### 1. 获取当前聊天窗口的聊天记录

```python
# 获取当前窗口聊天记录，并自动保存聊天图片
>>> msgs = wx.GetAllMessage(savepic=True)
```

wx.GetAllMessage

方法说明：

获取当前窗口中加载的所有聊天记录

参数：

| 参数名  | 类型 | 默认值 |         说明         |
| :-----: | :--: | :----: | :------------------: |
| savepic | bool | False  | 是否自动保存聊天图片 |

### 2. 打开指定好友聊天窗口

```python
# 打开“文件传输助手”聊天窗口
>>> who = '文件传输助手'
>>> wx.ChatWith(who)
```

wx.ChatWith

方法说明：

打开指定好友（群组）聊天窗口

参数：

| 参数名 | 类型 | 默认值 |            说明            |
| :----: | :--: | :----: | :------------------------: |
|  who   | str  |   /    | 要打开的聊天框好友名或群名 |

### 3. 发送消息

```python
# 给“文件传输助手”发送消息
>>> who = '文件传输助手'
>>> msg = '''这是一条消息
这是第二行
这是第三行
'''
>>> wx.SendMsg(msg, who=who)
```

wx.SendMsg

方法说明：

给指定人员（群组）发送消息

参数：

| 参数名 | 类型 | 默认值 |                  说明                  |
| :----: | :--: | :----: | :------------------------------------: |
|  msg   | str  |   /    |            要发送的文字内容            |
|  who   | str  |  None  | 要发送给谁，默认则发送给当前打开的页面 |
| clear  | bool |  True  |      是否清除原本聊天编辑框的内容      |
| at  | list,str |  None  | 要@的人，可以是一个人或多个人，格式为str或list，例如："张三"或["张三", "李四"] |

### 4. @所有人

```python
>>> who = '工作群'
>>> msg = '通知：XXXXXXXXXX'
>>> wx.AtAll(msg=msg, who=who)
```

wx.AtAll

方法说明：

@所有人

参数：

| 参数名 | 类型 | 默认值 |               说明               |
| :----: | :--: | :----: | :------------------------------: |
|  msg   | str  |  None  |     要发送的文字内容，可为空     |
|  who   | str  |  None  | 群名，默认则发送给当前打开的页面 |



### 5. 发送文件、图片

```python
# 给“文件传输助手”发送文件（图片同理）
>>> who = '文件传输助手'
# 指定文件路径（绝对路径）
>>> files = ['D:/test/test1.txt', 'D:/test/test2.txt', 'D:/test/test3.txt']
>>> wx.SendFiles(self, files, who=who)
```

wx.SendFiles

方法说明：

给指定人员（群组）发送文件或者图片

参数：

|  参数名  |    类型     | 默认值 |                  说明                   |
| :------: | :---------: | :----: | :-------------------------------------: |
| filepath | str \| list |   /    | 指定文件路径，单个文件str，多个文件list |
|   who    |     str     |  None  | 要发送给谁，默认则发送给当前打开的页面  |

### 6. 获取所有未读消息内容

```python
>>> msgs = wx.GetAllNewMessage()
```

wx.GetAllNewMessage

方法说明：

获取所有未读消息的内容，即存在未读数量小圆点的聊天窗

> 注：该方法暂时只能读取未开启消息免打扰的好友的未读消息，开启消息免打扰的聊天无法获取

### 7. 获取一个未读消息内容

```python
>>> msgs = wx.GetNextNewMessage()
>>> msgs
{'张三': [['张三', '哈哈哈', '42373591784181']]}
```

wx.GetNextNewMessage

方法说明：

只获取一个未读消息内容，这样多个聊天对象有新消息时，可以逐一获取消息内容并进行回复

| 参数名  | 类型 | 默认值 |       说明       |
| :-----: | :--: | :----: | :--------------: |
| savepic | bool | False  | 是否保存聊天图片 |

> 注：该方法暂时只能读取未开启消息免打扰的好友的未读消息，开启消息免打扰的聊天无法获取

### 8. 获取当前聊天窗口名

```python
>>> current = wx.CurrentChat()
```

wx.CurrentChat

方法说明：

获取当前聊天窗口名，即聊天窗口最上方的那个名字

> 注：该方法获取到的名字，如果是群组，则会带有群组人数，比如：闲置群（352）

### 9. 加载当前聊天页面更多聊天信息

```python
>>> wx.LoadMoreMessage()
```

wx.LoadMoreMessage

方法说明：

利用鼠标滚动加载当前聊天页面更多聊天信息

### 10. 监听指定好友（群聊）消息

#### 10.1 添加监听对象

```python
>>> wx.AddListenChat(who='张三', savepic=True)
```

wx.AddListenChat

方法说明：

将指定聊天对象独立出来，并且加入监听列表中

| 参数名  | 类型 | 默认值 |       说明       |
| :-----: | :--: | :----: | :--------------: |
| who | str | / | 好友名/群名 |
| savepic | bool | False | 是否保存聊天图片 |

#### 10.2 获取监听对象的新消息

```python
>>> msgs = wx.GetListenMessage()
>>> msgs
{'张三': [['张三', '哈哈哈', '42373591784181']],'李四': [['李四', '哈哈哈', '42373591784256']],'李白': []}
```

### 11. 接受新的好友申请

#### 11.1 获取新的好友申请对象列表

```python
>>> new = wx.GetNewFriends()
>>> new
[<wxauto New Friends Element at 0x1e95fced080 (张三: 你好,我是xxx群的张三)>,
<wxauto New Friends Element at 0x1e95fced081 (李四: 你好,我是xxx群的李四)>]
```

方法说明：

获取好友申请列表中，状态为可接受的好友申请对象

#### 11.2 通过好友申请对象接受好友请求

```python
# 获取第一个可接受的新好友对象
>>> new_friend1 = new[0]
>>> print(new_friend1.name)  # 获取好友申请昵称
张三
>>> print(new_friend1.msg)  # 获取好友申请信息
你好,我是xxx群的张三

# 接受好友请求，并且添加备注“备注张三”、添加标签wxauto
>>> new_friend1.Accept(remark='备注张三', tags=['wxauto'])
```

> 注：该方法接受好友请求后，并不会自动切换回聊天页面，需要配合调用11.1切换至聊天页面，否则其他有关聊天页面的方法不可使用

### 12. 切换微信页面

#### 12.1 切换到聊天页面

```python
>>> wx.SwitchToChat()
```

#### 12.2 切换到通讯录页面

```python
>>> wx.SwitchToContact()
```

### 13. 获取当前聊天成员列表

```python
>>> wx.GetGroupMembers()
['张三', '李四', '王五'...]
```

> 注：该方法获取到的为好友昵称或备注，有备注为备注，没备注为昵称

### 14. 获取所有好友列表

```python
>>> wx.GetAllFriends()
[{'nickname': '张三', 'remark': '张总', 'tags': None},
 {'nickname': '李四', 'remark': None, 'tags': ['同事', '初中同学']},
 {'nickname': '王五', 'remark': None, 'tags': None},
...]
```

| 参数名  | 类型 | 默认值 |       说明       |
| :-----: | :--: | :----: | :--------------: |
| keywords | str | None | 搜索关键词 |

> 注：1. 该方法运行时间取决于好友数量，约每秒6~8个好友的速度
> 
> 2. 该方法未经过大量测试，可能存在未知问题，如有问题请微信群内反馈

### 15. 发起好友申请

```python
>>> keywords = '13800000000'      # 微信号、手机号、QQ号
>>> addmsg = '你好，我是xxxx'      # 添加好友的消息
>>> remark = '备注名字'            # 备注名
>>> tags = ['朋友', '同事']        # 标签列表
>>> wx.AddNewFriend(keywords, addmsg=addmsg, remark=remark, tags=tags)
```

| 参数名  | 类型 | 默认值 |       说明       |
| :-----: | :--: | :----: | :--------------: |
| keywords | str | / | 微信号、手机号、QQ号 |
| addmsg | str | '你好，我是xxxx' | 添加好友的消息 |
| remark | str | None | 备注名 |

> 注：微信有一定的限制，如果频繁添加好友，可能会被限制添加好友的权限，所以请谨慎使用！！！


## 四、其他

### 1. 解决问题：微信提示版本低无法登录

3.9.8.15版本，使用以下方法打开微信登录窗口，即可成功登录
```python
from wxauto import FixVersionError

FixVersionError()
```

### 2. savepic保存图片默认路径设置

按以下设置即可
```python
from wxauto.elements import WxParam

WxParam.DEFALUT_IMAGE_SAVEPATH = r"D:\AAA\BBB"
```


## 五、使用案例

### 1. 监听指定群或好友消息并回复收到

```python
from wxauto import WeChat
import time

# 实例化微信对象
wx = WeChat()

# 指定监听目标
listen_list = [
    '张三',
    '李四',
    '工作群A',
    '工作群B'
]
for i in listen_list:
    wx.AddListenChat(who=i, savepic=True)  # 添加监听对象并且自动保存新消息图片

# 持续监听消息，并且收到消息后回复“收到”
wait = 10  # 设置10秒查看一次是否有新消息
while True:
    msgs = wx.GetListenMessage()
    for chat in msgs:
        one_msgs = msgs.get(chat)   # 获取消息内容
        # ===================================================
        # 处理消息逻辑
        # 
        # 处理消息内容的逻辑每个人都不同，按自己想法写就好了，这里不写了
        # 
        # ===================================================
        
        # 回复收到
        for msg in one_msgs:
            if msg.type == 'friend':
                chat.SendMsg('收到')  # 回复收到
    time.sleep(wait)
        
```

### 2. 监听所有未被屏蔽的新消息

```python
from wxauto import WeChat
import time

# 实例化微信对象
wx = WeChat()

# 持续监听消息，并且收到消息后回复“收到”
wait = 10  # 设置10秒查看一次是否有新消息
while True:
    msg = wx.GetNextNewMessage(savepic=True)
    # 如果获取到新消息了，则回复收到
    if msg and msg.type == 'friend':
        # ===================================================
        # 处理消息逻辑
        # 
        # 处理消息内容的逻辑每个人都不同，按自己想法写就好了，这里不写了
        # 
        # ===================================================

        wx.SendMsg(msg='收到', who=list(msg)[0])  # 回复收到
    time.sleep(wait)
        
```

## 五、云服务器部署

### 1. 购买云服务器

选个便宜的新用户大概60一年的就可以部署了
【[腾讯云](https://cloud.tencent.com/act/cps/redirect?redirect=5695&cps_key=348fc319f5c034afed4b7c6894f3883a&from=console)】
【[阿里云](https://www.aliyun.com/daily-act/ecs/activity_selection?userCode=t9ic9gas)】

内存：2G+

系统：WindowsServer2016、2019、2022版本

> 没试过1G的内存，我最小测试过2G的所以推荐至少2G

### 2. 远程控制

_由于windows系统自带的远程控制RDP(MSTSC)在结束远程时会自动锁屏，导致该项目无法正常运行，所以要更换其他远程控制软件。_

有很多远程方案，这里推荐使用VNC：

1. 登录服务器，安装RealVNC server，设置登录密码和服务端口，默认为5900端口，但是最好改一下

2. 登录云服务器服务商控制台，在防火墙打开上一步设置的vnc端口的访问权限
3. 自己电脑安装RealVNC viewer，输入云服务器ip:端口进行连接，断开连接不会锁屏
4. 服务器安装微信，部署代码即可运行

> 注：1. 远程方案有很多，没有必须是VNC，只要不锁屏用什么都可以，向日葵也可以。
>
> ​        2. 云服务器最好买你所在城市或临近城市的，因为有几率触发微信异地登录风控。

## 其他
如果遇到问题或者有新的想法，希望您可以通过以下两种方式联系我进行改进：
- 微信（请备注wxauto，若要加入交流群，请备注：wxauto交流群）：
- ![微信](https://github.com/cluic/wxauto/blob/WeChat3.9.8/utils/wxqrcode.png)

## 免责声明
代码仅供交流学习使用，请勿用于非法用途和商业用途！如因此产生任何法律纠纷，均与作者无关！
