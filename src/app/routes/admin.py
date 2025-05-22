from flask import request, jsonify, session
from app import app
from app.utils.auth import login_required, role_required
from mypy.db_operations import get_db_connection, add_record, update_record, delete_record, get_records

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
        conn = get_db_connection()
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

# 更新管理员个人资料API
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
        conn = get_db_connection()
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
