import sqlite3
import os

class Database(object):
    def __init__(self):
        self.group_db_file = 'data/database.db'
        self.user_db_file = 'data/user_database.db'
        self.group_conn = self.create_connection(self.group_db_file)
        self.user_conn = self.create_connection(self.user_db_file)
        # 创建表结构
        self.create_tables()

    def create_connection(self, db_file):
        """创建数据库连接"""
        if not os.path.isfile(db_file):
            print(f"数据库文件 {db_file} 不存在，将自动创建。")
        try:
            conn = sqlite3.connect(db_file)
            print(f"成功连接到数据库 {db_file}")
            return conn
        except sqlite3.Error as e:
            print(f"连接数据库时发生错误: {e}")
            return None

    def create_tables(self):
        """创建群聊表和用户白名单表"""
        try:
            # 创建群聊表
            self.group_conn.execute('''
                CREATE TABLE IF NOT EXISTS group_chat (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    iselect BOOLEAN
                )
            ''')
            print("群聊表创建成功")

            # 创建用户白名单表
            self.user_conn.execute('''
                CREATE TABLE IF NOT EXISTS user_whitelist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nickname TEXT,
                    remark TEXT,
                    tags TEXT
                )
            ''')
            print("用户白名单表创建成功")

            # 提交事务
            self.group_conn.commit()
            self.user_conn.commit()
        except sqlite3.Error as e:
            print(f"创建表时发生错误: {e}")

    def query_group_by_name(self, name):
        """根据群聊名称查询群聊信息"""
        try:
            cursor = self.group_conn.cursor()
            cursor.execute('SELECT * FROM group_chat WHERE name = ?', (name,))
            result = cursor.fetchall()
            cursor.close()
            return result
        except sqlite3.Error as e:
            print(f"查询群聊时发生错误: {e}")
            return None

    def query_user_by_nickname(self, nickname):
        """根据用户昵称查询用户白名单信息"""
        try:
            cursor = self.user_conn.cursor()
            cursor.execute('SELECT * FROM user_whitelist WHERE nickname = ?', (nickname,))
            result = cursor.fetchall()
            cursor.close()
            return result
        except sqlite3.Error as e:
            print(f"查询用户时发生错误: {e}")
            return None

    def query_all_users_nickname(self):
        """查询用户白名单表并返回所有用户的昵称和备注的字典"""
        try:
            cursor = self.user_conn.cursor()
            cursor.execute('SELECT nickname, remark FROM user_whitelist')
            rows = cursor.fetchall()
            users = {row[0]: row[1] for row in rows}  # 将昵称和备注转换为字典
            cursor.close()
            return users
        except sqlite3.Error as e:
            print(f"查询用户昵称和备注时发生错误: {e}")
            return {}

    def is_user_in_whitelist(self, identifier):
        """
        通过输入 nickname 或 remark 判断一个人是否在名单中
        :param identifier: 输入的昵称或备注
        :return: 如果在名单中返回 True，否则返回 False
        """
        try:
            cursor = self.user_conn.cursor()
            # 查询 nickname 或 remark 是否匹配
            cursor.execute('SELECT 1 FROM user_whitelist WHERE nickname = ? OR remark = ?', (identifier, identifier))
            result = cursor.fetchone()  # 获取查询结果
            cursor.close()
            return result is not None  # 如果有匹配项，返回 True，否则返回 False
        except sqlite3.Error as e:
            print(f"查询用户是否在名单中时发生错误: {e}")
            return False

    def insert_group_chat(self, name, iselect):
        """插入群聊信息"""
        try:
            cursor = self.group_conn.cursor()
            cursor.execute('INSERT INTO group_chat (name, iselect) VALUES (?, ?)', (name, iselect))
            self.group_conn.commit()
            last_id = cursor.lastrowid
            print(f"群聊信息插入成功：ID={last_id}, Name={name}, IsSelect={iselect}")
        except sqlite3.Error as e:
            print(f"插入群聊信息时发生错误: {e}")

    def insert_user_whitelist(self, nickname, remark, tags):
        """插入用户白名单信息"""
        try:
            user=self.query_user_by_nickname(nickname)

            if user:
                print(f"用户 {nickname} 已存在于白名单中。")
                return

            cursor = self.user_conn.cursor()
            cursor.execute('INSERT INTO user_whitelist (nickname, remark, tags) VALUES (?, ?, ?, ?)',
                           (nickname, remark, tags))
            self.user_conn.commit()
            last_id = cursor.lastrowid
            print(
                f"用户白名单信息插入成功：ID={last_id}, Nickname={nickname}, Remark={remark}, Tags={tags}")
        except sqlite3.Error as e:
            print(f"插入用户白名单信息时发生错误: {e}")

    def delete_group_chat_by_name(self, name):
        """根据群聊名称删除群聊信息"""
        try:
            cursor = self.group_conn.cursor()
            cursor.execute('DELETE FROM group_chat WHERE name = ?', (name,))
            self.group_conn.commit()
            print(f"群聊信息删除成功：Name={name}")
        except sqlite3.Error as e:
            print(f"删除群聊信息时发生错误: {e}")

    def delete_user_whitelist_by_nickname(self, nickname):
        """根据用户昵称删除用户白名单信息"""
        try:
            cursor = self.user_conn.cursor()
            cursor.execute('DELETE FROM user_whitelist WHERE nickname = ?', (nickname,))
            self.user_conn.commit()
            print(f"用户白名单信息删除成功：Nickname={nickname}")
        except sqlite3.Error as e:
            print(f"删除用户白名单信息时发生错误: {e}")

    def printall(self):
        """打印数据库中的所有内容"""
        try:
            # 查询群聊表
            cursor = self.group_conn.cursor()
            cursor.execute('SELECT * FROM group_chat')
            group_chats = cursor.fetchall()
            print("群聊表内容：")
            for row in group_chats:
                print(row)

            # 查询用户白名单表
            cursor = self.user_conn.cursor()
            cursor.execute('SELECT * FROM user_whitelist')
            user_whitelists = cursor.fetchall()
            print("用户白名单表内容：")
            for row in user_whitelists:
                print(row)

            cursor.close()
        except sqlite3.Error as e:
            print(f"打印数据库内容时发生错误: {e}")

    def close_connections(self):
        """关闭数据库连接"""
        if self.group_conn:
            self.group_conn.close()
            print("群聊数据库连接已关闭")
        if self.user_conn:
            self.user_conn.close()
            print("用户白名单数据库连接已关闭")

# 示例使用
if __name__ == "__main__":
    db = Database()
    db.printall()
    db.close_connections()



