from functools import wraps
from flask import session, jsonify, redirect, url_for

# 登录检查装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

# 添加角色检查装饰器
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                return redirect(url_for('index'))
            if 'role' not in session or session['role'] not in allowed_roles:
                return jsonify({'success': False, 'message': '您没有权限访问此功能'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
