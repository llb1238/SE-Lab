from flask import request, jsonify, session
from app import app
from app.utils.auth import login_required, role_required
from app.utils.db import get_db_connection

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
        conn = get_db_connection()
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
        conn = get_db_connection()
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

# 添加路由获取课程的所有学生成绩
@app.route('/api/course-grades', methods=['GET'])
@login_required
def get_course_grades():
    try:
        conn = get_db_connection()
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

# 保存所有成绩
@app.route('/api/course-grades', methods=['POST'])
@login_required
def save_course_grades():
    try:
        data = request.get_json()
        conn = get_db_connection()
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
