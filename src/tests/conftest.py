import os, sys
import sqlite3
# __file__ => src/tests/conftest.py，
# os.path.dirname(__file__) => src/tests，
# os.path.join(..., '..') => src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from run import app as flask_app
from app import config as mypy_config
from app.utils.db_init import init_db as mypy_init_db

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
    """每次测试前后，删除测试库并使用统一脚本初始化表结构并插入测试数据"""
    db_path = os.path.join(os.path.dirname(__file__), '../database/edu_system.db')
    if os.path.exists(db_path):
        os.remove(db_path)

    # 覆盖 DATABASE_PATH 并初始化（带测试数据）
    mypy_config.DATABASE_PATH = db_path
    mypy_init_db(insert_test_data=True)

    yield  # 测试运行

    # 测试完成后删除数据库文件
    if os.path.exists(db_path):
        os.remove(db_path)
