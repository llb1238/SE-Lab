from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import sys
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

# 静态文件路由
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/')
def index():
    if 'username' not in session:
        return render_template('login.html')
    return render_template('main.html')

# 添加用户表创建
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 创建用户表
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

# 确保在应用启动时创建表
init_db()

# 修改登录路由
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()

    if user and user['password'] == password:  # 在实际应用中应该使用密码哈希
        session['username'] = username
        return jsonify({'success': True, 'message': '登录成功'})

    return jsonify({'success': False, 'message': '用户名或密码错误'})

# 添加注册路由
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({
                'success': False,
                'message': '用户名和密码不能为空'
            }), 400

        conn = get_db()
        cursor = conn.cursor()

        # 检查用户名是否已存在
        cursor.execute('SELECT 1 FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return jsonify({
                'success': False,
                'message': '用户名已存在'
            }), 400

        # 添加新用户
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                    (username, password))  # 实际应用中应该哈希密码

        conn.commit()
        return jsonify({
            'success': True,
            'message': '注册成功'
        })

    except Exception as e:
        print('注册失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        conn.close()

@app.route('/main')
@login_required
def show_main():
    return render_template('main.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

# 页面路由
@app.route('/courses')
@login_required
def show_courses():
    return render_template('courses.html')

@app.route('/students')
@login_required
def show_students():
    return render_template('students.html')

@app.route('/teachers')
@login_required
def show_teachers():
    return render_template('teachers.html')

@app.route('/progress')
@login_required
def show_progress():
    return render_template('progress.html')

@app.route('/interaction')
@login_required
def show_interaction():
    return render_template('interaction.html')

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

@app.route('/api/students', methods=['POST'])
@login_required
def add_student():
    try:
        data = request.get_json()
        print('接收到的学生数据:', data)
        
        # 验证数据
        required_fields = ['name', 'student_id', 'enrollment_year']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'缺少必要字段: {field}'
                }), 400

        # 添加记录
        student_data = {
            'name': data['name'],
            'student_id': data['student_id'],
            'enrollment_year': int(data['enrollment_year'])
        }
        
        new_id = add_record('students', student_data)
        
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

# 获取学生课程
@app.route('/api/students/<student_id>/courses', methods=['GET'])
@login_required
def get_student_courses(student_id):
    try:
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

# 学生选课路由
@app.route('/api/student-courses', methods=['POST'])
@login_required
def add_student_course():
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        
        # 检查学生是否已选这门课
        cursor.execute('''
            SELECT 1 FROM student_courses 
            WHERE student_id = (
                SELECT id FROM students WHERE student_id = ?
            ) AND course_id = ?
        ''', (data['student_id'], data['course_id']))
        
        if cursor.fetchone():
            return jsonify({
                'success': False,
                'message': '该学生已经选择了这门课程'
            }), 400
            
        # 添加选课记录
        cursor.execute('''
            INSERT INTO student_courses (student_id, course_id)
            SELECT s.id, ? 
            FROM students s 
            WHERE s.student_id = ?
        ''', (data['course_id'], data['student_id']))
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': '选课成功'
        })
    except Exception as e:
        conn.rollback()
        print('选课失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
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
            SET name = ?, student_id = ?, enrollment_year = ?
            WHERE student_id = ?
        ''', (data['name'], data['student_id'], data['enrollment_year'], student_id))
        
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

if __name__ == '__main__':
    app.run(debug=True)