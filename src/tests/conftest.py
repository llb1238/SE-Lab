import os, sys
import sqlite3
# __file__ => src/tests/conftest.py，
# os.path.dirname(__file__) => src/tests，
# os.path.join(..., '..') => src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from edu_sys_main import app as flask_app

@pytest.fixture
def app():
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test_secret",
        "WTF_CSRF_ENABLED": False
    })
    yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture(scope="function", autouse=True)
def reset_database():
    """每次测试后删除测试数据库文件并重新初始化"""
    db_path = os.path.join(os.path.dirname(__file__), '../database/edu_system.db')
    if os.path.exists(db_path):
        os.remove(db_path)

    # 初始化数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

    yield  # 测试运行在此处

    # 测试完成后删除数据库文件
    if os.path.exists(db_path):
        os.remove(db_path)
