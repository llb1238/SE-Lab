from flask import request, jsonify, session
from app import app
from app.utils.auth import login_required, role_required
from app.utils.db import get_db_connection, add_record, update_record, delete_record, get_records

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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM users WHERE username = ? AND role = ?', (data['name'], 'teacher'))
        if not cursor.fetchone():
            # 创建用户账号，使用默认密码
            default_password = "123456"  # 在实际应用中应该生成随机密码并通知用户
            cursor.execute(
                'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                (data['name'], default_password, 'teacher')
            )
            conn.commit()
        
        return jsonify({
            'success': True,
            'message': '教师添加成功',
            'data': {'id': new_id}
        })
        
    except Exception as e:
        print('添加教师失败:', e)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/teachers/<teacher_id>', methods=['PUT'])
@login_required
def update_teacher(teacher_id):
    try:
        data = request.get_json()
        print('接收到的更新教师数据:', data)  # 添加日志
        
        conn = get_db_connection()
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

@app.route('/api/teachers/<teacher_id>', methods=['DELETE'])
@login_required
def delete_teacher(teacher_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取教师的内部ID和姓名
        cursor.execute('SELECT id, name FROM teachers WHERE teacher_id = ?', (teacher_id,))
        teacher = cursor.fetchone()
        if not teacher:
            return jsonify({
                'success': False,
                'message': '找不到该教师'
            }), 404
            
        teacher_internal_id = teacher['id']
        teacher_name = teacher['name']
        
        # 删除相关记录
        cursor.execute('DELETE FROM teacher_courses WHERE teacher_id = ?', (teacher_internal_id,))
        cursor.execute('DELETE FROM teachers WHERE id = ?', (teacher_internal_id,))
        # 删除对应的用户账号
        cursor.execute('DELETE FROM users WHERE username = ? AND role = ?', (teacher_name, 'teacher'))
        
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
        conn = get_db_connection()
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
        conn = get_db_connection()
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

# 获取教师课程API
@app.route('/api/teachers/<teacher_id>/courses', methods=['GET'])
@login_required
def get_teacher_courses(teacher_id):
    try:
        conn = get_db_connection()
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
        
        conn = get_db_connection()
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
