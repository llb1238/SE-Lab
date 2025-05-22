from flask import request, jsonify, session, redirect, url_for
import time
from app import app
from app.utils.db import get_db_connection

# 登录路由
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    
    if not role:
        return jsonify({'success': False, 'message': '请选择身份'}), 400
    
    conn = get_db_connection()
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

# 注册路由
@app.route('/register', methods=['POST'])
def register():
    conn = None  # 确保 finally 中可安全引用
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

        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查用户名是否已存在于相同角色
        cursor.execute('SELECT role FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        if row:
            existing_role = row[0]
            return jsonify({
                'success': False,
                'message': f'此用户名已被其他{existing_role}用户使用'
            }), 400

        print("未检测到重复用户名，继续注册")

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

# 注销路由
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    session.pop('student_id', None)
    session.pop('teacher_id', None)
    session.pop('admin_id', None)
    return redirect(url_for('index'))

# 获取当前用户信息API
@app.route('/api/current-user', methods=['GET'])
def get_current_user():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
        
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
