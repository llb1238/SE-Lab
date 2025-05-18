from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import sys
import time  # 添加时间模块导入
from functools import wraps

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from mypy.config import DATABASE_PATH
from mypy.db_operations import (
    get_db_connection, execute_query, execute_insert,
    execute_update, execute_delete, add_record,
    update_record, delete_record, get_records
)

app = Flask(__name__, static_url_path='/static')

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

# 使用 db_operations 中的函数替代直接的数据库操作
def get_db():
    return get_db_connection()

# 添加CORS headers
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

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

# 静态文件路由
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/')
def index():
    if 'username' not in session:
        return render_template('login.html')
    return render_template('main.html')

# 运行初始化脚本，确保学生表中enrollment_year可以为空
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 先创建用户表（如果不存在）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 检查users表是否存在role列
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    column_names = [column['name'] for column in columns]
    
    # 如果表中没有role列，添加它
    if 'role' not in column_names:
        print("正在向users表添加role列...")
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'teacher'")
    
    # 创建admin表（如果不存在）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        admin_id TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 更新students表，确保enrollment_year可以为NULL
    cursor.execute("PRAGMA table_info(students)")
    columns = cursor.fetchall()
    has_enrollment_year_constraint = False
    for column in columns:
        if column['name'] == 'enrollment_year' and column['notnull'] == 1:
            has_enrollment_year_constraint = True
            break
            
    if has_enrollment_year_constraint:
        # SQLite不支持直接修改列约束，需要重建表
        print("正在移除enrollment_year列的NOT NULL约束...")
        # 创建临时表
        cursor.execute('''
        CREATE TABLE students_temp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            student_id TEXT UNIQUE NOT NULL,
            enrollment_year INTEGER NULL
        )
        ''')
        # 复制数据
        cursor.execute('''
        INSERT INTO students_temp (id, name, student_id, enrollment_year)
        SELECT id, name, student_id, enrollment_year FROM students
        ''')
        # 删除原表
        cursor.execute("DROP TABLE students")
        # 重命名临时表
        cursor.execute("ALTER TABLE students_temp RENAME TO students")
    
    conn.commit()
    conn.close()

# 确保在应用启动时创建表
init_db()

# 修改登录路由，简化学生信息关联
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    
    if not role:
        return jsonify({'success': False, 'message': '请选择身份'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 验证用户凭据
    cursor.execute('SELECT * FROM users WHERE username = ? AND role = ?', (username, role))
    user = cursor.fetchone()

    if user and user['password'] == password:  # 在实际应用中应该使用密码哈希
        session['username'] = username
        session['role'] = role  # 保存用户角色到session
        
        # 如果是学生，查找并保存学生ID
        if role == 'student':
            cursor.execute('SELECT student_id FROM students WHERE name = ?', (username,))
            student = cursor.fetchone()
            if student:
                session['student_id'] = student['student_id']
                print(f"学生 {username} 登录成功，student_id: {student['student_id']}")
            else:
                # 找不到对应的学生记录，自动创建一个
                print(f"为用户 {username} 创建新的学生记录")
                new_student_id = f"S{username}{user['id']:04d}"
                
                try:
                    cursor.execute('''
                        INSERT INTO students (name, student_id) 
                        VALUES (?, ?)
                    ''', (username, new_student_id))
                    conn.commit()
                    session['student_id'] = new_student_id
                    print(f"为用户 {username} 创建学生记录成功，student_id: {new_student_id}")
                except Exception as e:
                    print(f"创建学生记录失败: {e}")
        
        # 如果是教师，查找并保存教师ID
        elif role == 'teacher':
            cursor.execute('SELECT teacher_id FROM teachers WHERE name = ?', (username,))
            teacher = cursor.fetchone()
            if teacher:
                session['teacher_id'] = teacher['teacher_id']
                print(f"教师 {username} 登录成功，teacher_id: {teacher['teacher_id']}")
            else:
                # 找不到对应的教师记录，自动创建一个
                new_teacher_id = f"T{username}{user['id']:04d}"
                
                try:
                    cursor.execute('''
                        INSERT INTO teachers (name, teacher_id) 
                        VALUES (?, ?)
                    ''', (username, new_teacher_id))
                    conn.commit()
                    session['teacher_id'] = new_teacher_id
                    print(f"为用户 {username} 创建教师记录成功，teacher_id: {new_teacher_id}")
                except Exception as e:
                    print(f"创建教师记录失败: {e}")
            
        # 特殊处理管理员角色
        elif role == 'admin':
            cursor.execute('SELECT admin_id FROM admins WHERE name = ?', (username,))
            admin = cursor.fetchone()
            if admin:
                session['admin_id'] = admin['admin_id']
                print(f"管理员 {username} 登录成功，admin_id: {admin['admin_id']}")
            else:
                # 找不到对应的管理员记录，自动创建一个
                new_admin_id = f"A{username}{user['id']:04d}"
                
                try:
                    cursor.execute('''
                        INSERT INTO admins (name, admin_id) 
                        VALUES (?, ?)
                    ''', (username, new_admin_id))
                    conn.commit()
                    session['admin_id'] = new_admin_id
                    print(f"为用户 {username} 创建管理员记录成功，admin_id: {new_admin_id}")
                except Exception as e:
                    print(f"创建管理员记录失败: {e}")
        
        return jsonify({'success': True, 'message': '登录成功', 'role': role})
    
    return jsonify({'success': False, 'message': '用户名、密码或身份选择错误'})

# 修改注册逻辑，处理学生记录时不指定enrollment_year
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')
        admin_code = data.get('admin_code')
        
        if not username or not password or not role:
            return jsonify({
                'success': False,
                'message': '用户名、密码和身份不能为空'
            }), 400
        
        # 验证管理员验证码
        if role == 'admin':
            if not admin_code:
                return jsonify({
                    'success': False,
                    'message': '请输入管理员验证码'
                }), 400
            
            if admin_code != '1':  # 设置验证码为1
                return jsonify({
                    'success': False,
                    'message': '管理员验证码错误'
                }), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # 检查用户名是否已存在于相同角色
        cursor.execute('SELECT 1 FROM users WHERE username = ? AND role = ?', (username, role))
        if cursor.fetchone():
            return jsonify({
                'success': False,
                'message': f'此用户名已被其他{role}用户使用'
            }), 400

        # 添加新用户
        cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                      (username, password, role))
        
        # 获取新插入用户的ID
        user_id = cursor.lastrowid
        
        # 根据角色在对应表中创建关联记录
        if role == 'student':
            # 创建学生ID，格式: S + 用户名 + 用户ID序号
            student_id = f"S{username}{user_id:04d}"
            
            # 检查学生ID是否已存在
            cursor.execute('SELECT 1 FROM students WHERE student_id = ?', (student_id,))
            if cursor.fetchone():
                student_id = f"S{username}{user_id}_{int(time.time())}"  # 确保唯一性
                
            try:
                # 在students表中创建对应记录 - 不指定enrollment_year
                cursor.execute('''
                    INSERT INTO students (name, student_id) 
                    VALUES (?, ?)
                ''', (username, student_id))
                
                print(f"为新注册用户 {username} 创建学生记录，student_id: {student_id}")
            except Exception as e:
                # 如果上述插入失败，可能是字段约束问题，尝试使用默认年份
                print(f"创建学生记录失败: {e}")
                current_year = time.localtime().tm_year
                cursor.execute('''
                    INSERT INTO students (name, student_id, enrollment_year) 
                    VALUES (?, ?, ?)
                ''', (username, student_id, current_year))
                print(f"使用默认年份创建学生记录: {student_id}, 年份: {current_year}")
            
        elif role == 'teacher':
            # 创建教师ID，格式: T + 用户名 + 用户ID序号
            teacher_id = f"T{username}{user_id:04d}"
            
            # 检查教师ID是否已存在
            cursor.execute('SELECT 1 FROM teachers WHERE teacher_id = ?', (teacher_id,))
            if cursor.fetchone():
                teacher_id = f"T{username}{user_id}_{int(time.time())}"  # 确保唯一性
                
            # 在teachers表中创建对应记录
            cursor.execute('''
                INSERT INTO teachers (name, teacher_id) 
                VALUES (?, ?)
            ''', (username, teacher_id))
            
            print(f"为新注册用户 {username} 创建教师记录，teacher_id: {teacher_id}")
        
        elif role == 'admin':
            # 创建管理员ID，格式: A + 用户名 + 用户ID序号
            admin_id = f"A{username}{user_id:04d}"
            
            # 检查管理员ID是否已存在
            cursor.execute('SELECT 1 FROM admins WHERE admin_id = ?', (admin_id,))
            if cursor.fetchone():
                admin_id = f"A{username}{user_id}_{int(time.time())}"  # 确保唯一性
                
            # 在admins表中创建对应记录
            cursor.execute('''
                INSERT INTO admins (name, admin_id) 
                VALUES (?, ?)
            ''', (username, admin_id))
            
            print(f"为新注册用户 {username} 创建管理员记录，admin_id: {admin_id}")
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': '注册成功'
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print('注册失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/main')
@login_required
def show_main():
    role = session.get('role', '')
    return render_template('main.html', role=role)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    session.pop('student_id', None)
    session.pop('teacher_id', None)
    session.pop('admin_id', None)
    return redirect(url_for('index'))

# 页面路由
@app.route('/courses')
@login_required
@role_required(['admin'])  # 只允许管理员访问课程管理
def show_courses():
    return render_template('courses.html')

@app.route('/students')
@login_required
@role_required(['admin'])  # 只允许管理员访问学生管理
def show_students():
    return render_template('students.html')

@app.route('/teachers')
@login_required
@role_required(['admin'])  # 只允许管理员访问教师管理
def show_teachers():
    return render_template('teachers.html')

@app.route('/progress')
@login_required
@role_required(['teacher'])  # 只允许教师访问成绩管理
def show_progress():
    return render_template('progress.html', role=session.get('role', ''))

@app.route('/interaction')
@login_required
@role_required(['teacher'])  # 只允许教师访问作业管理
def show_interaction():
    return render_template('interaction.html', role=session.get('role', ''))

# 学生专有页面路由
@app.route('/student/courses')
@login_required
@role_required(['student'])  # 只允许学生角色访问
def show_student_courses():
    """显示学生课程页面，包括已选课程和可选课程"""
    return render_template('student/courses.html')

@app.route('/student/progress')
@login_required
@role_required(['student'])
def show_student_progress():
    return render_template('student/progress.html')

@app.route('/student/assignments')
@login_required
@role_required(['student'])
def show_student_assignments():
    return render_template('student/assignments.html')

# 学生个人资料页面路由
@app.route('/student/profile')
@login_required
@role_required(['student'])
def show_student_profile():
    return render_template('student/profile.html')

# 教师个人资料页面路由
@app.route('/teacher/profile')
@login_required
@role_required(['teacher'])
def show_teacher_profile():
    return render_template('teacher/profile.html')

# 管理员个人资料页面路由
@app.route('/admin/profile')
@login_required
@role_required(['admin'])
def show_admin_profile():
    return render_template('admin/profile.html')

# API路由
@app.route('/api/courses', methods=['GET'])
@login_required
def get_courses():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses ORDER BY name")
        courses = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'data': courses,
            'message': '获取课程列表成功'
        })
    except Exception as e:
        print('获取课程列表失败:', e)
        return jsonify({
            'success': False,
            'message': str(e),
            'data': []
        }), 500
    finally:
        conn.close()

@app.route('/api/courses', methods=['POST'])
@login_required
def add_course():
    try:
        data = request.get_json()
        print('接收到的课程数据:', data)
        
        # 验证数据
        required_fields = ['name', 'learn_time', 'credit', 'usual_score', 
                         'midterm_score', 'final_score']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'缺少必要字段: {field}'
                }), 400

        # 添加记录
        course_data = {
            'name': data['name'],
            'learn_time': data['learn_time'],
            'credit': float(data['credit']),
            'usual_score': int(data['usual_score']),
            'midterm_score': int(data['midterm_score']),
            'final_score': int(data['final_score']),
            'times': data.get('times', '')
        }
        
        new_id = add_record('courses', course_data)
        
        return jsonify({
            'success': True,
            'message': '课程添加成功',
            'data': {'id': new_id}
        })
        
    except sqlite3.IntegrityError as e:
        print('数据完整性错误:', e)
        return jsonify({
            'success': False,
            'message': '课程名已存在'
        }), 400
    except Exception as e:
        print('添加课程失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/courses/<int:course_id>', methods=['PUT'])
@login_required
def update_course(course_id):
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        
        # 检查课程名是否已存在（如果修改了课程名）
        cursor.execute("SELECT id FROM courses WHERE name = ? AND id != ?", 
                      (data['name'], course_id))
        if cursor.fetchone():
            return jsonify({
                'success': False,
                'message': '课程名已存在'
            }), 400
            
        # 更新课程信息
        sql = """UPDATE courses 
                SET name=?, learn_time=?, credit=?, 
                    usual_score=?, midterm_score=?, final_score=?, times=? 
                WHERE id=?"""
        cursor.execute(sql, (
            data['name'],
            data['learn_time'],
            float(data['credit']),
            int(data['usual_score']),
            int(data['midterm_score']),
            int(data['final_score']),
            data.get('times', ''),
            course_id
        ))
        
        conn.commit()
        
        # 获取更新后的课程信息
        cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
        updated_course = cursor.fetchone()
        
        return jsonify({
            'success': True,
            'message': '课程更新成功',
            'data': dict(updated_course) if updated_course else None
        })
        
    except Exception as e:
        print('更新课程失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        conn.close()

@app.route('/api/courses/<int:course_id>', methods=['DELETE'])
@login_required
def delete_course(course_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 检查课程是否存在
        cursor.execute('SELECT id FROM courses WHERE id = ?', (course_id,))
        if not cursor.fetchone():
            return jsonify({
                'success': False,
                'message': '找不到该课程'
            }), 404
        
        # 删除相关记录
        cursor.execute('DELETE FROM student_courses WHERE course_id = ?', (course_id,))
        cursor.execute('DELETE FROM teacher_courses WHERE course_id = ?', (course_id,))
        cursor.execute('DELETE FROM grades WHERE course_id = ?', (course_id,))
        cursor.execute('DELETE FROM assignments WHERE course_id = ?', (course_id,))
        cursor.execute('DELETE FROM courses WHERE id = ?', (course_id,))
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': '课程删除成功'
        })
    except Exception as e:
        if conn:
            conn.rollback()
        print('删除课程失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

# 学生API路由
@app.route('/api/students', methods=['GET'])
@login_required
def get_students():
    try:
        students = get_records('students')
        print("获取到的学生数据:", [dict(student) for student in students])  # 添加调试日志
        return jsonify({
            'success': True,
            'data': [dict(student) for student in students],
            'message': '获取学生列表成功'
        })
    except Exception as e:
        print('获取学生列表失败:', e)
        return jsonify({
            'success': False,
            'message': str(e),
            'data': []
        }), 500

# 修改学生API路由，处理enrollment_year参数
@app.route('/api/students', methods=['POST'])
@login_required
@role_required(['admin'])  # 只允许管理员添加学生
def add_student():
    try:
        data = request.get_json()
        print('接收到的学生数据:', data)
        
        # 验证数据
        required_fields = ['name', 'student_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'缺少必要字段: {field}'
                }), 400

        # 添加记录 - 使用name和student_id，可选enrollment_year
        student_data = {
            'name': data['name'],
            'student_id': data['student_id']
        }
        
        # 如果提供了入学年份，添加到数据中
        if 'enrollment_year' in data and data['enrollment_year']:
            student_data['enrollment_year'] = data['enrollment_year']
        
        try:
            # 尝试插入学生记录
            new_id = add_record('students', student_data)
        except sqlite3.IntegrityError as e:
            if 'NOT NULL constraint failed' in str(e) and 'enrollment_year' in str(e):
                # 如果遇到enrollment_year的NOT NULL约束，添加默认年份
                student_data['enrollment_year'] = time.localtime().tm_year
                new_id = add_record('students', student_data)
            else:
                raise
        
        # 检查是否有相同名称的用户账号，没有则自动创建
        cursor = get_db().cursor()
        cursor.execute('SELECT 1 FROM users WHERE username = ? AND role = ?', (data['name'], 'student'))
        if not cursor.fetchone():
            # 创建用户账号，使用默认密码
            default_password = "123456"  # 在实际应用中应该生成随机密码并通知用户
            cursor.execute(
                'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                (data['name'], default_password, 'student')
            )
            get_db().commit()
        
        return jsonify({
            'success': True,
            'message': '学生添加成功',
            'data': {'id': new_id}
        })
        
    except sqlite3.IntegrityError as e:
        print('数据完整性错误:', e)
        return jsonify({
            'success': False,
            'message': '学号已存在'
        }), 400
    except Exception as e:
        print('添加学生失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# 教师API路由
@app.route('/api/teachers', methods=['GET'])
@login_required
def get_teachers():
    try:
        teachers = get_records('teachers')
        print("获取到的教师数据:", [dict(teacher) for teacher in teachers])  # 添加调试日志
        return jsonify({
            'success': True,
            'data': [dict(teacher) for teacher in teachers],
            'message': '获取教师列表成功'
        })
    except Exception as e:
        print('获取教师列表失败:', e)
        return jsonify({
            'success': False,
            'message': str(e),
            'data': []
        }), 500

@app.route('/api/teachers', methods=['POST'])
@login_required
@role_required(['admin'])  # 只允许管理员添加教师
def add_teacher():
    try:
        data = request.get_json()
        print('接收到的教师数据:', data)
        
        # 验证数据
        required_fields = ['name', 'teacher_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'缺少必要字段: {field}'
                }), 400

        # 添加记录
        teacher_data = {
            'name': data['name'],
            'teacher_id': data['teacher_id']
        }
        
        new_id = add_record('teachers', teacher_data)
        
        # 检查是否有相同名称的用户账号，没有则自动创建
        cursor = get_db().cursor()
        cursor.execute('SELECT 1 FROM users WHERE username = ? AND role = ?', (data['name'], 'teacher'))
        if not cursor.fetchone():
            # 创建用户账号，使用默认密码
            default_password = "123456"  # 在实际应用中应该生成随机密码并通知用户
            cursor.execute(
                'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                (data['name'], default_password, 'teacher')
            )
            get_db().commit()
        
        return jsonify({
            'success': True,
            'message': '教师添加成功',
            'data': {'id': new_id}
        })
        
    except sqlite3.IntegrityError as e:
        print('数据完整性错误:', e)
        return jsonify({
            'success': False,
            'message': '教师号已存在'
        }), 400
    except Exception as e:
        print('添加教师失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# 获取学生课程API
@app.route('/api/students/<student_id>/courses', methods=['GET'])
@login_required
def get_student_courses(student_id):
    """获取特定学生的所有已选课程"""
    try:
        # 如果是学生，检查是否是查询自己的信息
        if session.get('role') == 'student':
            if session.get('student_id') != student_id:
                return jsonify({
                    'success': False,
                    'message': '您只能查看自己的课程'
                }), 403
    
        # 获取学生选择的课程
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.* 
            FROM courses c
            JOIN student_courses sc ON c.id = sc.course_id
            JOIN students s ON sc.student_id = s.id
            WHERE s.student_id = ?
        ''', (student_id,))
        
        courses = [dict(row) for row in cursor.fetchall()]
        return jsonify({
            'success': True,
            'data': courses,
            'message': '获取学生课程成功'
        })
    except Exception as e:
        print('获取学生课程失败:', e)
        return jsonify({
            'success': False,
            'message': str(e),
            'data': []
        }), 500
    finally:
        conn.close()

# 获取教师课程
@app.route('/api/teachers/<teacher_id>/courses', methods=['GET'])
@login_required
def get_teacher_courses(teacher_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.* 
            FROM courses c
            JOIN teacher_courses tc ON c.id = tc.course_id
            JOIN teachers t ON tc.teacher_id = t.id
            WHERE t.teacher_id = ?
        ''', (teacher_id,))
        
        courses = [dict(row) for row in cursor.fetchall()]
        return jsonify({
            'success': True,
            'data': courses,
            'message': '获取教师课程成功'
        })
    except Exception as e:
        print('获取教师课程失败:', e)
        return jsonify({
            'success': False,
            'message': str(e),
            'data': []
        }), 500
    finally:
        conn.close()

# 添加新的API路由，获取当前登录教师的课程
@app.route('/api/teacher-courses/current', methods=['GET'])
@login_required
@role_required(['teacher'])  # 只允许教师访问
def get_current_teacher_courses():
    """获取当前登录教师的所有课程"""
    try:
        teacher_id = session.get('teacher_id')
        if not teacher_id:
            return jsonify({
                'success': False,
                'message': '未找到教师信息'
            }), 404
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.* 
            FROM courses c
            JOIN teacher_courses tc ON c.id = tc.course_id
            JOIN teachers t ON tc.teacher_id = t.id
            WHERE t.teacher_id = ?
        ''', (teacher_id,))
        
        courses = [dict(row) for row in cursor.fetchall()]
        return jsonify({
            'success': True,
            'data': courses,
            'message': '获取教师课程成功'
        })
    except Exception as e:
        print('获取当前教师课程失败:', e)
        return jsonify({
            'success': False,
            'message': str(e),
            'data': []
        }), 500
    finally:
        conn.close()

# 获取特定课程的学生列表
@app.route('/api/courses/<int:course_id>/students', methods=['GET'])
@login_required
def get_course_students(course_id):
    """获取选了特定课程的所有学生"""
    try:
        # 如果是教师，验证该课程是否是自己教授的
        if session.get('role') == 'teacher':
            teacher_id = session.get('teacher_id')
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 1 FROM teacher_courses tc
                JOIN teachers t ON tc.teacher_id = t.id
                WHERE t.teacher_id = ? AND tc.course_id = ?
            ''', (teacher_id, course_id))
            
            if not cursor.fetchone():
                return jsonify({
                    'success': False,
                    'message': '您没有权限查看该课程的学生'
                }), 403
            
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.* 
            FROM students s
            JOIN student_courses sc ON s.id = sc.student_id
            WHERE sc.course_id = ?
        ''', (course_id,))
        
        students = [dict(row) for row in cursor.fetchall()]
        return jsonify({
            'success': True,
            'data': students,
            'message': '获取课程学生成功'
        })
    except Exception as e:
        print('获取课程学生失败:', e)
        return jsonify({
            'success': False,
            'message': str(e),
            'data': []
        }), 500
    finally:
        conn.close()

# 安排教师课程
@app.route('/api/teacher-courses', methods=['POST'])
@login_required
def add_teacher_course():
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        
        # 检查教师是否已经安排了这门课
        cursor.execute('''
            SELECT 1 FROM teacher_courses 
            WHERE teacher_id = (
                SELECT id FROM teachers WHERE teacher_id = ?
            ) AND course_id = ?
        ''', (data['teacher_id'], data['course_id']))
        
        if cursor.fetchone():
            return jsonify({
                'success': False,
                'message': '该教师已经安排了这门课程'
            }), 400
            
        # 添加教师课程记录
        cursor.execute('''
            INSERT INTO teacher_courses (teacher_id, course_id)
            SELECT t.id, ? 
            FROM teachers t 
            WHERE t.teacher_id = ?
        ''', (data['course_id'], data['teacher_id']))
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': '课程安排成功'
        })
    except Exception as e:
        conn.rollback()
        print('安排课程失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        conn.close()

# 学生选课路由增强
@app.route('/api/student-courses', methods=['POST'])
@login_required
def add_student_course():
    """学生选课功能"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        course_id = data.get('course_id')
        
        # 如果是学生，检查是否是为自己选课
        if session.get('role') == 'student':
            if session.get('student_id') != student_id:
                return jsonify({
                    'success': False,
                    'message': '您只能为自己选课'
                }), 403
        
        conn = get_db()
        cursor = conn.cursor()

        # 检查学生是否已选这门课
        cursor.execute('''
            SELECT 1 FROM student_courses
            WHERE student_id = (
                SELECT id FROM students WHERE student_id = ?
            ) AND course_id = ?
        ''', (student_id, course_id))
        
        if cursor.fetchone():
            return jsonify({
                'success': False,
                'message': '您已经选择了这门课程'
            }), 400
        
        # 获取学生内部ID
        cursor.execute('SELECT id FROM students WHERE student_id = ?', (student_id,))
        student = cursor.fetchone()
        if not student:
            return jsonify({
                'success': False,
                'message': '找不到学生信息'
            }), 404
        
        # 获取要选的课程时间
        cursor.execute('SELECT times FROM courses WHERE id = ?', (course_id,))
        new_course = cursor.fetchone()
        if not new_course:
            return jsonify({
                'success': False,
                'message': '找不到课程信息'
            }), 404
        
        # 获取学生已选课程时间
        cursor.execute('''
            SELECT c.times 
            FROM courses c
            JOIN student_courses sc ON c.id = sc.course_id
            WHERE sc.student_id = ? AND c.times IS NOT NULL
        ''', (student['id'],))
        
        existing_courses = cursor.fetchall()
        
        # 检查时间冲突
        if new_course['times']:
            new_times = new_course['times'].split('|')
            
            for course in existing_courses:
                if course['times']:
                    existing_times = course['times'].split('|')
                    
                    # 检查每个时间段是否有冲突
                    for new_time in new_times:
                        if new_time in existing_times:
                            return jsonify({
                                'success': False,
                                'message': f'时间冲突：您在{new_time}已有其他课程'
                            }), 400
        
        # 添加选课记录
        cursor.execute('''
            INSERT INTO student_courses (student_id, course_id)
            VALUES (?, ?)
        ''', (student['id'], course_id))
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': '选课成功'
        })
    except Exception as e:
        if conn:
            conn.rollback()
        print('选课失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

# 添加退课API
@app.route('/api/student-courses', methods=['DELETE'])
@login_required
def drop_student_course():
    """学生退课功能"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        course_id = data.get('course_id')
        
        # 如果是学生，检查是否是为自己退课
        if session.get('role') == 'student':
            if session.get('student_id') != student_id:
                return jsonify({
                    'success': False, 
                    'message': '您只能退自己的课'
                }), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        # 获取学生内部ID
        cursor.execute('SELECT id FROM students WHERE student_id = ?', (student_id,))
        student = cursor.fetchone()
        if not student:
            return jsonify({
                'success': False,
                'message': '找不到学生信息'
            }), 404
        
        # 删除选课记录
        cursor.execute('''
            DELETE FROM student_courses 
            WHERE student_id = ? AND course_id = ?
        ''', (student['id'], course_id))
        
        if cursor.rowcount == 0:
            return jsonify({
                'success': False,
                'message': '未找到选课记录'
            }), 404
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': '退课成功'
        })
    except Exception as e:
        if conn:
            conn.rollback()
        print('退课失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

# 成绩相关路由
@app.route('/api/course-grades', methods=['GET'])
@login_required
def get_course_grades():
    try:
        conn = get_db()
        cursor = conn.cursor()

        # 获取所有课程及其学生成绩
        cursor.execute('''
            SELECT c.*, s.name as student_name, s.student_id,
                g.usual_grade, g.midterm_grade, g.final_grade
            FROM courses c
            LEFT JOIN grades g ON c.id = g.course_id
            LEFT JOIN students s ON g.student_id = s.id
            ORDER BY c.id, s.name
        ''')

        courses = {}
        for row in cursor.fetchall():
            row_dict = dict(row)
            course_id = row_dict['id']
            if course_id not in courses:
                courses[course_id] = {
                    'id': course_id,
                    'name': row_dict['name'],
                    'students': []
                }
            if row_dict['student_name']:
                courses[course_id]['students'].append({
                    'name': row_dict['student_name'],
                    'student_id': row_dict['student_id'],
                    'usual_grade': row_dict['usual_grade'] or 0,
                    'midterm_grade': row_dict['midterm_grade'] or 0,
                    'final_grade': row_dict['final_grade'] or 0
                })

        return jsonify({
            'success': True,
            'data': list(courses.values()),
            'message': '获取成绩数据成功'
        })
    except Exception as e:
        print('获取成绩数据失败:', e)
        return jsonify({
            'success': False,
            'message': str(e),
            'data': []
        }), 500

# 保存成绩
@app.route('/api/course-grades', methods=['POST'])
@login_required
def save_course_grades():
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()

        for grade in data['grades']:
            cursor.execute('''
                INSERT OR REPLACE INTO grades
                (student_id, course_id, usual_grade, midterm_grade, final_grade)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                grade['student_id'],
                grade['course_id'],
                grade['usual_grade'],
                grade['midterm_grade'],
                grade['final_grade']
            ))

        conn.commit()
        return jsonify({
            'success': True,
            'message': '成绩保存成功'
        })
    except Exception as e:
        print('保存成绩失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# 删除相关路由
@app.route('/api/students/<student_id>', methods=['DELETE'])
@login_required
def delete_student(student_id):
    try:
        conn = get_db()
        cursor = conn.cursor()

        # 获取学生的内部ID
        cursor.execute('SELECT id FROM students WHERE student_id = ?', (student_id,))
        student = cursor.fetchone()
        if not student:
            return jsonify({
                'success': False,
                'message': '找不到该学生'
            }), 404

        student_internal_id = student['id']

        # 删除相关的选课记录
        cursor.execute('DELETE FROM student_courses WHERE student_id = ?', (student_internal_id,))
        # 删除相关的成绩记录
        cursor.execute('DELETE FROM grades WHERE student_id = ?', (student_internal_id,))
        # 删除学生
        cursor.execute('DELETE FROM students WHERE id = ?', (student_internal_id,))

        conn.commit()
        return jsonify({
            'success': True,
            'message': '学生删除成功'
        })
    except Exception as e:
        conn.rollback()
        print('删除学生失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if 'conn' in locals() and conn:  # 检查 conn 是否已定义
            conn.close()

@app.route('/api/teachers/<teacher_id>', methods=['DELETE'])
@login_required
def delete_teacher(teacher_id):
    try:
        conn = get_db()
        cursor = conn.cursor()

        # 获取教师的内部ID
        cursor.execute('SELECT id FROM teachers WHERE teacher_id = ?', (teacher_id,))
        teacher = cursor.fetchone()
        if not teacher:
            return jsonify({
                'success': False,
                'message': '找不到该教师'
            }), 404
            
        teacher_internal_id = teacher['id']
        
        # 删除相关记录
        cursor.execute('DELETE FROM teacher_courses WHERE teacher_id = ?', (teacher_internal_id,))
        cursor.execute('DELETE FROM teachers WHERE id = ?', (teacher_internal_id,))
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': '教师删除成功'
        })
    except Exception as e:
        if conn:
            conn.rollback()
        print('删除教师失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

# 作业相关路由
@app.route('/api/assignments', methods=['POST'])
@login_required
def create_assignment():
    try:
        data = request.get_json()
        print("接收到的作业数据:", data)
        
        if not data or 'course_id' not in data or 'title' not in data or 'content' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必要的作业信息'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查课程是否存在
        cursor.execute('SELECT id FROM courses WHERE id = ?', (data['course_id'],))
        if not cursor.fetchone():
            return jsonify({
                'success': False,
                'message': '课程不存在'
            }), 404
        
        # 插入作业
        cursor.execute('''
            INSERT INTO assignments (course_id, title, content)
            VALUES (?, ?, ?)
        ''', (data['course_id'], data['title'], data['content']))
        
        conn.commit()
        
        # 获取新插入的作业ID
        new_id = cursor.lastrowid
        
        # 返回新创建的作业信息
        cursor.execute('''
            SELECT id, course_id, title, content, create_time
            FROM assignments
            WHERE id = ?
        ''', (new_id,))
        
        new_assignment = dict(cursor.fetchone())
        
        return jsonify({
            'success': True,
            'message': '作业发布成功',
            'data': new_assignment
        })
    except sqlite3.Error as e:
        print('数据库错误:', str(e))
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'message': f'数据库错误: {str(e)}'
        }), 500
    except Exception as e:
        print('发布作业失败:', str(e))
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'message': f'发布作业失败: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/courses/<int:course_id>/assignments', methods=['GET'])
@login_required
def get_assignments_by_course(course_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, course_id, title, content, create_time
            FROM assignments 
            WHERE course_id = ?
            ORDER BY create_time DESC
        ''', (course_id,))
        
        assignments = [dict(row) for row in cursor.fetchall()]
        return jsonify({
            'success': True,
            'data': assignments,
            'message': '获取作业列表成功'
        })
    except Exception as e:
        print('获取作业列表失败:', e)
        return jsonify({
            'success': False,
            'message': str(e),
            'data': []
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/assignments/<int:assignment_id>', methods=['PUT'])
@login_required
def modify_assignment(assignment_id):
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE assignments 
            SET title = ?, content = ?
            WHERE id = ?
        ''', (data['title'], data['content'], assignment_id))
        
        if cursor.rowcount == 0:
            return jsonify({
                'success': False,
                'message': '找不到该作业'
            }), 404
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': '作业更新成功'
        })
    except Exception as e:
        conn.rollback()
        print('更新作业失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        conn.close()

@app.route('/api/assignments/<int:assignment_id>', methods=['DELETE'])
@login_required
def remove_assignment(assignment_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM assignments WHERE id = ?', (assignment_id,))
        
        if cursor.rowcount == 0:
            return jsonify({
                'success': False,
                'message': '找不到该作业'
            }), 404
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': '作业删除成功'
        })
    except Exception as e:
        conn.rollback()
        print('删除作业失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        conn.close()

# 更新学生信息
@app.route('/api/students/<student_id>', methods=['PUT'])
@login_required
def update_student(student_id):
    try:
        data = request.get_json()
        print('接收到的更新学生数据:', data)  # 添加日志
        
        conn = get_db()
        cursor = conn.cursor()
        
        # 检查新学号是否已存在（如果修改了学号且不是当前学生）
        if data['student_id'] != student_id:
            cursor.execute("SELECT id FROM students WHERE student_id = ?", (data['student_id'],))
            if cursor.fetchone():
                return jsonify({
                    'success': False,
                    'message': '新学号已存在'
                }), 400
        
        # 更新学生信息
        cursor.execute('''
            UPDATE students 
            SET name = ?, student_id = ?
            WHERE student_id = ?
        ''', (data['name'], data['student_id'], student_id))
        
        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({
                'success': False,
                'message': '未找到要更新的学生'
            }), 404
        
        conn.commit()
        
        # 获取更新后的学生信息
        cursor.execute("SELECT * FROM students WHERE student_id = ?", (data['student_id'],))
        updated_student = cursor.fetchone()
        
        print('更新后的学生数据:', dict(updated_student) if updated_student else None)  # 添加日志
        
        return jsonify({
            'success': True,
            'message': '学生信息更新成功',
            'data': dict(updated_student) if updated_student else None
        })
        
    except Exception as e:
        print('更新学生信息失败:', e)  # 添加日志
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

# 更新教师信息
@app.route('/api/teachers/<teacher_id>', methods=['PUT'])
@login_required
def update_teacher(teacher_id):
    try:
        data = request.get_json()
        print('接收到的更新教师数据:', data)  # 添加日志
        
        conn = get_db()
        cursor = conn.cursor()
        
        # 检查新教师号是否已存在（如果修改了教师号且不是当前教师）
        if data['teacher_id'] != teacher_id:
            cursor.execute("SELECT id FROM teachers WHERE teacher_id = ?", (data['teacher_id'],))
            if cursor.fetchone():
                return jsonify({
                    'success': False,
                    'message': '新教师号已存在'
                }), 400
        
        # 更新教师信息
        cursor.execute('''
            UPDATE teachers 
            SET name = ?, teacher_id = ?
            WHERE teacher_id = ?
        ''', (data['name'], data['teacher_id'], teacher_id))
        
        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({
                'success': False,
                'message': '未找到要更新的教师'
            }), 404
        
        conn.commit()
        
        # 获取更新后的教师信息
        cursor.execute("SELECT * FROM teachers WHERE teacher_id = ?", (data['teacher_id'],))
        updated_teacher = cursor.fetchone()
        
        print('更新后的教师数据:', dict(updated_teacher) if updated_teacher else None)  # 添加日志
        
        return jsonify({
            'success': True,
            'message': '教师信息更新成功',
            'data': dict(updated_teacher) if updated_teacher else None
        })
        
    except Exception as e:
        print('更新教师信息失败:', e)  # 添加日志
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

# 成绩相关路由
@app.route('/api/students/<student_id>/grades', methods=['GET'])
@login_required
def get_student_grades(student_id):
    # 如果是学生，只能查看自己的成绩
    if session.get('role') == 'student':
        if session.get('student_id') != student_id:
            return jsonify({
                'success': False,
                'message': '您只能查看自己的成绩'
            }), 403
    
    # 继续原有逻辑
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 获取学生选择的所有课程及其成绩
        cursor.execute('''
            SELECT c.*, g.usual_grade, g.midterm_grade, g.final_grade
            FROM courses c
            LEFT JOIN grades g ON c.id = g.course_id
            JOIN student_courses sc ON c.id = sc.course_id
            JOIN students s ON sc.student_id = s.id
            WHERE s.student_id = ?
        ''', (student_id,))
        
        courses = [dict(row) for row in cursor.fetchall()]
        return jsonify({
            'success': True,
            'data': courses,
            'message': '获取成绩成功'
        })
    except Exception as e:
        print('获取成绩失败:', e)
        return jsonify({
            'success': False,
            'message': str(e),
            'data': []
        }), 500
    finally:
        conn.close()

@app.route('/api/grades', methods=['POST'])
@login_required
def save_grades():
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        
        # 获取学生的内部ID
        cursor.execute('SELECT id FROM students WHERE student_id = ?', (data['student_id'],))
        student = cursor.fetchone()
        if not student:
            return jsonify({
                'success': False,
                'message': '找不到该学生'
            }), 404
            
        # 保存成绩
        for grade in data['grades']:
            cursor.execute('''
                INSERT OR REPLACE INTO grades 
                (student_id, course_id, usual_grade, midterm_grade, final_grade)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                student['id'],
                grade['course_id'],
                grade['usual_grade'],
                grade['midterm_grade'],
                grade['final_grade']
            ))
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': '成绩保存成功'
        })
    except Exception as e:
        conn.rollback()
        print('保存成绩失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        conn.close()

# 添加获取当前用户信息的API，增加学生ID/教师ID/管理员ID信息
@app.route('/api/current-user', methods=['GET'])
@login_required
def get_current_user():
    user_data = {
        'username': session.get('username', ''),
        'role': session.get('role', '')
    }
    
    # 添加学生、教师或管理员特定的信息
    if session.get('role') == 'student':
        user_data['student_id'] = session.get('student_id')
    elif session.get('role') == 'teacher':
        user_data['teacher_id'] = session.get('teacher_id')
    elif session.get('role') == 'admin':
        user_data['admin_id'] = session.get('admin_id')
    
    return jsonify({
        'success': True,
        'data': user_data
    })

# 获取学生个人资料API
@app.route('/api/students/<student_id>/profile', methods=['GET'])
@login_required
def get_student_profile(student_id):
    # 检查权限：只能查看自己的资料
    if session.get('role') == 'student' and session.get('student_id') != student_id:
        return jsonify({
            'success': False,
            'message': '您只能查看自己的个人资料'
        }), 403
        
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 获取学生信息
        cursor.execute('SELECT * FROM students WHERE student_id = ?', (student_id,))
        student = cursor.fetchone()
        
        if not student:
            return jsonify({
                'success': False,
                'message': '找不到该学生信息'
            }), 404
            
        return jsonify({
            'success': True,
            'data': dict(student),
            'message': '获取学生个人资料成功'
        })
    except Exception as e:
        print('获取学生个人资料失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        conn.close()

# 更新学生个人资料API（包括密码修改）
@app.route('/api/students/<student_id>/profile', methods=['PUT'])
@login_required
def update_student_profile(student_id):
    # 检查权限：只能修改自己的资料
    if session.get('role') == 'student' and session.get('student_id') != student_id:
        return jsonify({
            'success': False,
            'message': '您只能修改自己的个人资料'
        }), 403
        
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        
        # 检查学生是否存在
        cursor.execute('SELECT * FROM students WHERE student_id = ?', (student_id,))
        student = cursor.fetchone()
        
        if not student:
            return jsonify({
                'success': False,
                'message': '找不到该学生信息'
            }), 404
            
        # 如果要修改学号，检查新学号是否已被占用（且不是自己）
        if data['student_id'] != student_id:
            cursor.execute('SELECT 1 FROM students WHERE student_id = ? AND id != ?', 
                          (data['student_id'], student['id']))
            if cursor.fetchone():
                return jsonify({
                    'success': False,
                    'message': '该学号已被其他学生使用'
                }), 400
                
        # 更新学生信息
        cursor.execute('''
            UPDATE students 
            SET name = ?, student_id = ?, enrollment_year = ?
            WHERE student_id = ?
        ''', (data['name'], data['student_id'], data.get('enrollment_year'), student_id))
        
        # 如果提供了新密码，更新密码
        if 'new_password' in data and data['new_password']:
            cursor.execute('''
                UPDATE users 
                SET password = ?
                WHERE username = ?
            ''', (data['new_password'], student['name']))
            
        # 如果修改了学号，更新session中的学号
        if data['student_id'] != student_id:
            session['student_id'] = data['student_id']
            
        conn.commit()
        
        # 获取更新后的信息
        cursor.execute('SELECT * FROM students WHERE student_id = ?', (data['student_id'],))
        updated_student = cursor.fetchone()
        
        return jsonify({
            'success': True,
            'data': dict(updated_student) if updated_student else None,
            'message': '学生个人资料更新成功'
        })
    except Exception as e:
        print('更新学生个人资料失败:', e)
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

# 获取教师个人资料API
@app.route('/api/teachers/<teacher_id>/profile', methods=['GET'])
@login_required
def get_teacher_profile(teacher_id):
    # 检查权限：只能查看自己的资料
    if session.get('role') == 'teacher' and session.get('teacher_id') != teacher_id:
        return jsonify({
            'success': False,
            'message': '您只能查看自己的个人资料'
        }), 403
        
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 获取教师信息
        cursor.execute('SELECT * FROM teachers WHERE teacher_id = ?', (teacher_id,))
        teacher = cursor.fetchone()
        
        if not teacher:
            return jsonify({
                'success': False,
                'message': '找不到该教师信息'
            }), 404
            
        return jsonify({
            'success': True,
            'data': dict(teacher),
            'message': '获取教师个人资料成功'
        })
    except Exception as e:
        print('获取教师个人资料失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        conn.close()

# 更新教师个人资料API（包括密码修改）
@app.route('/api/teachers/<teacher_id>/profile', methods=['PUT'])
@login_required
def update_teacher_profile(teacher_id):
    # 检查权限：只能修改自己的资料
    if session.get('role') == 'teacher' and session.get('teacher_id') != teacher_id:
        return jsonify({
            'success': False,
            'message': '您只能修改自己的个人资料'
        }), 403
        
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        
        # 检查教师是否存在
        cursor.execute('SELECT * FROM teachers WHERE teacher_id = ?', (teacher_id,))
        teacher = cursor.fetchone()
        
        if not teacher:
            return jsonify({
                'success': False,
                'message': '找不到该教师信息'
            }), 404
            
        # 如果要修改教师ID，检查新ID是否已被占用（且不是自己）
        if data['teacher_id'] != teacher_id:
            cursor.execute('SELECT 1 FROM teachers WHERE teacher_id = ? AND id != ?', 
                          (data['teacher_id'], teacher['id']))
            if cursor.fetchone():
                return jsonify({
                    'success': False,
                    'message': '该教师ID已被其他教师使用'
                }), 400
                
        # 更新教师信息
        cursor.execute('''
            UPDATE teachers 
            SET name = ?, teacher_id = ?
            WHERE teacher_id = ?
        ''', (data['name'], data['teacher_id'], teacher_id))
        
        # 如果提供了新密码，更新密码
        if 'new_password' in data and data['new_password']:
            cursor.execute('''
                UPDATE users 
                SET password = ?
                WHERE username = ?
            ''', (data['new_password'], teacher['name']))
            
        # 如果修改了教师ID，更新session中的教师ID
        if data['teacher_id'] != teacher_id:
            session['teacher_id'] = data['teacher_id']
            
        conn.commit()
        
        # 获取更新后的信息
        cursor.execute('SELECT * FROM teachers WHERE teacher_id = ?', (data['teacher_id'],))
        updated_teacher = cursor.fetchone()
        
        return jsonify({
            'success': True,
            'data': dict(updated_teacher) if updated_teacher else None,
            'message': '教师个人资料更新成功'
        })
    except Exception as e:
        print('更新教师个人资料失败:', e)
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

# 获取管理员个人资料API
@app.route('/api/admins/<admin_id>/profile', methods=['GET'])
@login_required
def get_admin_profile(admin_id):
    # 检查权限：只能查看自己的资料
    if session.get('role') == 'admin' and session.get('admin_id') != admin_id:
        return jsonify({
            'success': False,
            'message': '您只能查看自己的个人资料'
        }), 403
        
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 获取管理员信息
        cursor.execute('SELECT * FROM admins WHERE admin_id = ?', (admin_id,))
        admin = cursor.fetchone()
        
        if not admin:
            return jsonify({
                'success': False,
                'message': '找不到该管理员信息'
            }), 404
            
        return jsonify({
            'success': True,
            'data': dict(admin),
            'message': '获取管理员个人资料成功'
        })
    except Exception as e:
        print('获取管理员个人资料失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        conn.close()

# 更新管理员个人资料API（包括密码修改）
@app.route('/api/admins/<admin_id>/profile', methods=['PUT'])
@login_required
def update_admin_profile(admin_id):
    # 检查权限：只能修改自己的资料
    if session.get('role') == 'admin' and session.get('admin_id') != admin_id:
        return jsonify({
            'success': False,
            'message': '您只能修改自己的个人资料'
        }), 403
        
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        
        # 检查管理员是否存在
        cursor.execute('SELECT * FROM admins WHERE admin_id = ?', (admin_id,))
        admin = cursor.fetchone()
        
        if not admin:
            return jsonify({
                'success': False,
                'message': '找不到该管理员信息'
            }), 404
            
        # 如果要修改管理员ID，检查新ID是否已被占用（且不是自己）
        if data['admin_id'] != admin_id:
            cursor.execute('SELECT 1 FROM admins WHERE admin_id = ? AND id != ?', 
                          (data['admin_id'], admin['id']))
            if cursor.fetchone():
                return jsonify({
                    'success': False,
                    'message': '该管理员ID已被其他管理员使用'
                }), 400
                
        # 更新管理员信息
        cursor.execute('''
            UPDATE admins 
            SET name = ?, admin_id = ?
            WHERE admin_id = ?
        ''', (data['name'], data['admin_id'], admin_id))
        
        # 如果提供了新密码，更新密码
        if 'new_password' in data and data['new_password']:
            cursor.execute('''
                UPDATE users 
                SET password = ?
                WHERE username = ?
            ''', (data['new_password'], admin['name']))
            
        # 如果修改了管理员ID，更新session中的管理员ID
        if data['admin_id'] != admin_id:
            session['admin_id'] = data['admin_id']
            
        conn.commit()
        
        # 获取更新后的信息
        cursor.execute('SELECT * FROM admins WHERE admin_id = ?', (data['admin_id'],))
        updated_admin = cursor.fetchone()
        
        return jsonify({
            'success': True,
            'data': dict(updated_admin) if updated_admin else None,
            'message': '管理员个人资料更新成功'
        })
    except Exception as e:
        print('更新管理员个人资料失败:', e)
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)