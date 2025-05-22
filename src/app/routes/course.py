from flask import request, jsonify, session
from app import app
from app.utils.auth import login_required, role_required
from mypy.db_operations import get_db_connection, add_record, get_records

# 课程API路由
@app.route('/api/courses', methods=['GET'])
@login_required
def get_courses():
    try:
        conn = get_db_connection()
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
        conn = get_db_connection()
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
        conn = get_db_connection()
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

# 学生选课路由
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
        
        conn = get_db_connection()
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

# 退课API
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
        
        conn = get_db_connection()
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

# 安排教师课程
@app.route('/api/teacher-courses', methods=['POST'])
@login_required
def add_teacher_course():
    try:
        data = request.get_json()
        conn = get_db_connection()
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

# 获取特定课程的学生列表
@app.route('/api/courses/<int:course_id>/students', methods=['GET'])
@login_required
def get_course_students(course_id):
    """获取选了特定课程的所有学生"""
    try:
        # 如果是教师，验证该课程是否是自己教授的
        if session.get('role') == 'teacher':
            teacher_id = session.get('teacher_id')
            conn = get_db_connection()
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
            
        conn = get_db_connection()
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
