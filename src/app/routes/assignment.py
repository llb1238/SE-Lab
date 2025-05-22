from flask import request, jsonify, session
from app import app
from app.utils.auth import login_required, role_required
from mypy.db_operations import get_db_connection

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
    except Exception as e:
        print('发布作业失败:', e)
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
        conn = get_db_connection()
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
        conn = get_db_connection()
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
