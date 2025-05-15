import os

# 获取当前脚本所在的目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 确保数据库目录存在
DATABASE_DIR = os.path.join(os.path.dirname(BASE_DIR), 'database')
if not os.path.exists(DATABASE_DIR):
    os.makedirs(DATABASE_DIR)

# 数据库文件路径
DATABASE_PATH = os.path.join(DATABASE_DIR, 'edu_system.db')

# 数据库配置
DATABASE_CONFIG = {
    'database': DATABASE_PATH,
    'check_same_thread': False  # 允许多线程访问
}

