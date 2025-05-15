import os, sys
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
