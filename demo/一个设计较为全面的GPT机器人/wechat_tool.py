import json
import threading
import time
import tkinter as tk
from tkinter import messagebox, END
from pypinyin import lazy_pinyin
from wxauto import WeChat

import robot_manager
from database import Database
from robot_manager import RobotManager


class WeChatTool:
    def __init__(self, root):
        self.root = root
        self.root.title("微信自动回复工具")
        self.wechat = WeChat()
        self.database = None
        self.white_list = None
        self.SessionList = None
        self.friends = self.wechat.GetAllFriends()
        self.session = self.wechat.GetSession()
        self.robot_manager = RobotManager(self.wechat)
        self.listening = False
        self.listener_thread = None
        self.init_listener_thread()
        self.user_messages = {}
        self.create_widgets()
        self.keywords = []
        self.load_JSON('json/keywords.json')
        if not self.robot_manager.robots == []:
            self.add_robot_init()

    def load_JSON(self, filename):
        # 读取 JSON 文件
        with open(filename, 'r', encoding='utf-8') as file:
            data = json.load(file)
            self.keywords = data['keywords']
        print("Loaded keywords:", self.keywords)

    def init_database(self):
        """初始化数据库"""
        self.database = Database()
        self.white_list = self.database.query_all_users_nickname()

    def init_listener_thread(self):
        """初始化监听线程"""
        self.listener_thread = threading.Thread(target=self.listen_message)
        self.listener_thread.start()

    def create_widgets(self):
        # 更新按钮
        update_button = tk.Button(self.root, text="更新好友列表", command=self.update)
        update_button.pack()

        # 启动监听按钮
        start_listening_button = tk.Button(self.root, text="启动监听", command=self.start_listening)
        start_listening_button.pack()

        # 停止监听按钮
        stop_listening_button = tk.Button(self.root, text="停止监听", command=self.stop_listening)
        stop_listening_button.pack()

        # 搜索好友输入框
        self.search_entry = tk.Entry(self.root, width=50)
        self.search_entry.pack()

        # 搜索按钮
        search_button = tk.Button(self.root, text="搜索好友",
                                  command=lambda: self.search_contacts(self.search_entry, self.left_listbox))
        search_button.pack()

        # 创建左右两个Listbox
        left_frame = tk.Frame(self.root)
        left_frame.pack(side=tk.LEFT, padx=30, pady=30)
        right_frame = tk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT, padx=30, pady=30)

        left_label = tk.Label(left_frame, text="所有好友")
        left_label.pack()
        self.left_listbox = tk.Listbox(left_frame, width=30, height=15)
        self.left_listbox.pack()

        right_label = tk.Label(right_frame, text="白名单好友")
        right_label.pack()
        self.right_listbox = tk.Listbox(right_frame, width=30, height=15)
        self.right_listbox.pack()

        # 填充左边Listbox
        for friend in self.friends:
            self.left_listbox.insert(END, friend.get('nickname', '默认值'))

        # 绑定双击事件
        self.left_listbox.bind("<Double-Button-1>", self.move_to_right)
        self.right_listbox.bind("<Double-Button-1>", self.move_to_left)

        # 保存白名单按钮
        save_button = tk.Button(self.root, text="保存白名单", command=self.save_white_list)
        save_button.pack()

        # 机器人管理区域
        robot_frame = tk.Frame(self.root)
        robot_frame.pack(side=tk.BOTTOM, padx=30, pady=30)

        robot_label = tk.Label(robot_frame, text="机器人管理")
        robot_label.pack()

        # 机器人名称输入框
        self.robot_name_entry = tk.Entry(robot_frame, width=30)
        self.robot_name_entry.pack()
        self.robot_name_entry.insert(0, "机器人名称")  # 设置默认值

        # 机器人人设输入框
        self.robot_persona_entry = tk.Entry(robot_frame, width=30)
        self.robot_persona_entry.pack()
        self.robot_persona_entry.insert(0, "机器人人设")  # 设置默认值

        # 添加机器人按钮
        add_robot_button = tk.Button(robot_frame, text="添加机器人", command=self.add_robot)
        add_robot_button.pack()

        # 机器人列表
        self.robot_listbox = tk.Listbox(robot_frame, width=30, height=10)
        self.robot_listbox.pack()

        # 删除机器人按钮
        delete_robot_button = tk.Button(robot_frame, text="删除机器人", command=self.delete_robot)
        delete_robot_button.pack()

    def update(self):
        self.SessionList = self.wechat.GetSessionList()
        self.friends = self.wechat.GetAllFriends()
        self.left_listbox.delete(0, END)
        for friend in self.friends:
            self.left_listbox.insert(END, friend.get('nickname', '默认值'))

    def open_all_chats(self):
        """
        打开微信中所有的聊天界面
        """
        print("开始打开所有聊天窗口...")
        self.wechat._show()  # 确保微信窗口可见
        self.wechat.SwitchToChat()  # 切换到聊天页面

        # 获取所有聊天对象
        session_dict = self.wechat.GetSessionList(reset=True)  # 获取所有聊天对象，重置会话列表
        print("获取到的聊天对象：", session_dict)

        for session_name in session_dict:
            self.wechat.ChatWith(session_name)  # 打开每个聊天窗口
            time.sleep(0.01)  # 等待1秒，避免操作过快导致微信客户端卡顿

        print("所有聊天窗口已打开完成")

    def listen_message(self):
        self.init_database()
        self.open_all_chats()
        while True:
            print("wait for listen message.......")
            while self.listening:
                msgs = self.wechat.GetAllNewMessage()
                print("msgs:",msgs)
                if msgs:
                    for name, messages in msgs.items():
                        print("name:", name)
                        # 检查用户是否在白名单中
                        if not self.database.is_user_in_whitelist(name):
                            print("message:",messages)
                            if not 'Self' in str(messages):
                                messages=messages[-1]
                                print("message:", messages)
                                for word in self.keywords:
                                    if word in str(messages):
                                        print(f"检测到关键字：{word}")
                                        messages=str(messages)
                                        self.robot_manager.handle_message(messages, name)
                                        break
                                    else:
                                        print(f"未检测到关键字：{word}")
                time.sleep(1)
            time.sleep(1)

    def start_listening(self):
        if not self.listening:
            print("start listening")
            self.listening = True
            print(self.listening)

    def stop_listening(self):
        if self.listening:
            print("stop listening")
            self.listening = False
            if self.listener_thread:
                self.listener_thread.join()

    def move_to_right(self, event):
        selection = self.left_listbox.curselection()
        if selection:
            index = selection[0]
            friend = self.left_listbox.get(index)
            self.right_listbox.insert(END, friend)
            self.left_listbox.delete(index)

    def move_to_left(self, event):
        selection = self.right_listbox.curselection()
        if selection:
            index = selection[0]
            friend = self.right_listbox.get(index)
            self.left_listbox.insert(END, friend)
            self.right_listbox.delete(index)

    def save_white_list(self):
        white_list = [self.right_listbox.get(i) for i in range(self.right_listbox.size())]
        for nickname in white_list:
            for friend in self.friends:
                if friend.get('nickname') == nickname:
                    self.database.insert_user_whitelist(friend.get('nickname'), friend.get('remark'), friend.get('tag'))
        messagebox.showinfo("提示", "白名单已保存！")

    def search_contacts(self, search_entry, left_listbox):
        keyword = search_entry.get().strip()
        if not keyword:
            messagebox.showwarning("提示", "请输入搜索关键词！")
            return
        all_contacts = self.friends
        all_contacts_str = [str(contact) for contact in all_contacts]
        filtered_contacts = []
        for contact in all_contacts_str:
            pinyin_str = ''.join(lazy_pinyin(contact))
            if keyword.lower() in pinyin_str.lower() or keyword in contact:
                filtered_contacts.append(contact)
        left_listbox.delete(0, END)
        for contact in filtered_contacts:
            left_listbox.insert(END, contact)

    def add_robot(self):
        name = self.robot_name_entry.get().strip()
        persona = self.robot_persona_entry.get().strip()
        if not name or not persona:
            messagebox.showwarning("提示", "请输入机器人名称和人设！")
            return
        self.robot_manager.add_robot_config(name, persona, [])
        self.robot_listbox.insert(END, name + ' ' + persona)
        messagebox.showinfo("提示", "机器人添加成功！")

    def add_robot_init(self):
        for robot in self.robot_manager.robots:
            name = robot.name
            persona = robot.persona
            self.robot_listbox.insert(END, name + ' ' + persona)

    def delete_robot(self):
        selection = self.robot_listbox.curselection()
        if selection:
            index = selection[0]
            name = self.robot_listbox.get(index)
            self.robot_manager.delete_robot_config(name)
            self.robot_listbox.delete(index)
            messagebox.showinfo("提示", "机器人删除成功！")



