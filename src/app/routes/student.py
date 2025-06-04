from flask import request, jsonify, session
from app import app
from app.utils.auth import login_required, role_required
from app.utils.db import get_db_connection, add_record, update_record, delete_record, get_records

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
@role_required(['admin'])  # 只允许管理员添加学生
def add_student():
    conn = None
    try:
        data = request.get_json()
        print('接收到的学生数据:', data)
        
        # 验证数据
        required_fields = ['name', 'student_id', 'username']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'缺少必要字段: {field}'
                }), 400

        # 检查学生ID是否已存在
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM students WHERE student_id = ?', (data['student_id'],))
        if cursor.fetchone():
            return jsonify({
                'success': False,
                'message': f'学生ID {data["student_id"]} 已存在'
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
        except Exception as e:
            if 'NOT NULL constraint failed' in str(e) and 'enrollment_year' in str(e):
                # 如果遇到enrollment_year的NOT NULL约束，添加默认年份
                import time
                student_data['enrollment_year'] = time.localtime().tm_year
                new_id = add_record('students', student_data)
            else:
                raise
        
        # 检查是否有相同用户名的用户账号，没有则自动创建
        try:
            # 使用username而不是name来检查用户是否存在
            cursor.execute('SELECT 1 FROM users WHERE username = ? AND role = ?', (data['username'], 'student'))
            if not cursor.fetchone():
                # 创建用户账号，使用默认密码
                default_password = "123456"  # 在实际应用中应该生成随机密码并通知用户
                cursor.execute(
                    'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                    (data['username'], default_password, 'student')
                )
                conn.commit()
        except Exception as e:
            print(f'创建用户账号时出错: {e}')
            # 即使创建用户账号失败，学生记录已经创建成功，不回滚
        
        return jsonify({
            'success': True,
            'message': '学生添加成功',
            'data': {'id': new_id}
        })
        
    except Exception as e:
        print('添加学生失败:', e)
        if conn:
            conn.close()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/students/<student_id>', methods=['PUT'])
@login_required
def update_student(student_id):
    try:
        data = request.get_json()
        print('接收到的更新学生数据:', data)  # 添加日志
        
        conn = get_db_connection()
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

@app.route('/api/students/<student_id>', methods=['DELETE'])
@login_required
def delete_student(student_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取学生的内部ID和姓名
        cursor.execute('SELECT id, name FROM students WHERE student_id = ?', (student_id,))
        student = cursor.fetchone()
        if not student:
            return jsonify({
                'success': False,
                'message': '找不到该学生'
            }), 404

        student_internal_id = student['id']
        student_name = student['name']

        # 删除相关的选课记录
        cursor.execute('DELETE FROM student_courses WHERE student_id = ?', (student_internal_id,))
        # 删除相关的成绩记录
        cursor.execute('DELETE FROM grades WHERE student_id = ?', (student_internal_id,))
        # 删除学生
        cursor.execute('DELETE FROM students WHERE id = ?', (student_internal_id,))
        # 删除对应的用户账号
        cursor.execute('DELETE FROM users WHERE username = ? AND role = ?', (student_name, 'student'))

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
        conn = get_db_connection()
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
        conn = get_db_connection()
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
        conn = get_db_connection()
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
