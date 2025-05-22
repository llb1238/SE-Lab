from flask import Flask
from flask_cors import CORS
import os

app = Flask(__name__,
            static_url_path='/static',
            static_folder='../static',
            template_folder='../templates')

# CORS配置
CORS(app, supports_credentials=True, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000", "http://127.0.0.1:5000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

app.secret_key = 'your_secret_key'

# 添加CORS headers
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# 静态文件路由
from flask import send_from_directory

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('../static', filename)

# 导入路由 - 调整更合理的导入顺序
from app.auth.routes import *    # 移动到routes目录下
from app.routes.page import *    
from app.routes.course import *  # 基础数据先导入
from app.routes.student import * 
from app.routes.teacher import *
from app.routes.admin import *
from app.routes.grade import *    
from app.routes.assignment import *
