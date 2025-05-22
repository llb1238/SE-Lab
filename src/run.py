"""
教学管理系统主入口
通过此文件运行应用程序
"""
from app import app
from app.utils.db_init import init_db

# 确保在应用启动时初始化数据库
init_db()

if __name__ == '__main__':
    # 先显示启动消息，再运行应用
    print("服务器正在启动，请访问 http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
