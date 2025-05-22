import os

# 数据库路径
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'edu_system.db')

# 应用配置
SECRET_KEY = 'your_secret_key'
DEBUG = True
