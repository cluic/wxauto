"""
多语言关键字尚未收集完整，欢迎多多pull requests帮忙补充，感谢
"""

MAIN_LANGUAGE = {
    # 导航栏
    '导航': {'cn': '导航', 'cn_t': '', 'en': 'Navigation'},
    '聊天': {'cn': '聊天', 'cn_t': '', 'en': 'Chats'},
    '通讯录': {'cn': '通讯录', 'cn_t': '', 'en': 'Contacts'},
    '收藏': {'cn': '收藏', 'cn_t': '', 'en': 'Favorites'},
    '聊天文件': {'cn': '聊天文件', 'cn_t': '', 'en': 'Chat Files'},
    '朋友圈': {'cn': '朋友圈', 'cn_t': '', 'en': 'Moments'},
    '小程序面板': {'cn': '小程序面板', 'cn_t': '', 'en': 'Mini Programs Panel'},
    '手机': {'cn': '手机', 'cn_t': '', 'en': 'Phone'},
    '设置及其他': {'cn': '设置及其他', 'cn_t': '', 'en': 'Settings and Others'},
    
    # 好友列表栏
    '搜索': {'cn': '搜索', 'cn_t': '', 'en': 'Search'},
    '发起群聊': {'cn': '发起群聊', 'cn_t': '', 'en': 'Start Group Chat'},
    '文件传输助手': {'cn': '文件传输助手', 'cn_t': '', 'en': 'File Transfer'},
    '订阅号': {'cn': '订阅号', 'cn_t': '', 'en': 'Subscriptions'},
    '消息': {'cn': '消息', 'cn_t': '', 'en': ''},
    
    # 右上角工具栏
    '置顶': {'cn': '置顶', 'cn_t': '', 'en': 'Sticky on Top'},
    '最小化': {'cn': '最小化', 'cn_t': '', 'en': 'Minimize'},
    '最大化': {'cn': '最大化', 'cn_t': '', 'en': ''},
    '关闭': {'cn': '关闭', 'cn_t': '', 'en': ''},
    
    # 聊天框
    '聊天信息': {'cn': '聊天信息', 'cn_t': '', 'en': 'Chat Info'},
    '表情': {'cn': '表情', 'cn_t': '', 'en': 'Sticker'},
    '发送文件': {'cn': '发送文件', 'cn_t': '', 'en': 'Send File'},
    '截图': {'cn': '截图', 'cn_t': '', 'en': 'Screenshot'},
    '聊天记录': {'cn': '聊天记录', 'cn_t': '', 'en': 'Chat History'},
    '语音聊天': {'cn': '语音聊天', 'cn_t': '', 'en': 'Voice Call'},
    '视频聊天': {'cn': '视频聊天', 'cn_t': '', 'en': 'Video Call'},
    '发送': {'cn': '发送', 'cn_t': '', 'en': 'Send'},
    '输入': {'cn': '输入', 'cn_t': '', 'en': 'Enter'},
    
    # 消息类型
    '链接': {'cn': '链接', 'cn_t': '', 'en': 'Link'},
    '视频': {'cn': '视频', 'cn_t': '', 'en': 'Video'},
    '图片': {'cn': '图片', 'cn_t': '', 'en': 'Photo'},
    '文件': {'cn': '文件', 'cn_t': '', 'en': 'File'},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''}
}

IMAGE_LANGUAGE = {
    '上一张': {'cn': '上一张', 'cn_t': '', 'en': 'Previous'},
    '下一张': {'cn': '下一张', 'cn_t': '', 'en': 'Next'},
    '预览': {'cn': '预览', 'cn_t': '', 'en': 'Preview'},
    '放大': {'cn': '放大', 'cn_t': '', 'en': 'Zoom'},
    '缩小': {'cn': '缩小', 'cn_t': '', 'en': 'Shrink'},
    '图片原始大小': {'cn': '图片原始大小', 'cn_t': '', 'en': 'Original image size'},
    '旋转': {'cn': '旋转', 'cn_t': '', 'en': 'Rotate'},
    '编辑': {'cn': '编辑', 'cn_t': '', 'en': 'Edit'},
    '翻译': {'cn': '翻译', 'cn_t': '', 'en': 'Translate'},
    '提取文字': {'cn': '提取文字', 'cn_t': '', 'en': 'Extract Text'},
    '识别图中二维码': {'cn': '识别图中二维码', 'cn_t': '', 'en': 'Extract QR Code'},
    '另存为...': {'cn': '另存为...', 'cn_t': '', 'en': 'Save as…'},
    '更多': {'cn': '更多', 'cn_t': '', 'en': 'More'},
    '最小化': {'cn': '最小化', 'cn_t': '', 'en': 'Minimize'},
    '最大化': {'cn': '最大化', 'cn_t': '', 'en': 'Maximize'},
    '关闭': {'cn': '关闭', 'cn_t': '', 'en': 'Close'},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''},
    '': {'cn': '', 'cn_t': '', 'en': ''}
}

WARNING = {
    '版本不一致': {
        'cn': '当前微信客户端版本为{}，与当前库版本{}不一致，可能会导致部分功能无法正常使用，请注意判断',
        'cn_t': '當前微信客戶端版本為{}，與當前庫版本{}不一致，可能會導致部分功能無法正常使用，請注意判斷',
        'en': 'The current WeChat client version is {}, which is inconsistent with the current library version {}, which may cause some functions to fail to work properly. Please pay attention to judgment'
    }
}
