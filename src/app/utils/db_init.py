from app.utils.db import get_db_connection
import os
import sys
import time
from datetime import datetime

def init_db(insert_test_data=False):
    """
    初始化数据库，创建所需的表和结构
    
    参数:
        insert_test_data: 是否插入测试数据
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 创建表结构
        create_tables(cursor)
        
        # 如果需要，插入测试数据
        if insert_test_data:
            add_test_data(cursor)
            
        conn.commit()
        print("数据库初始化完成")
    except Exception as e:
        conn.rollback()
        print(f"数据库初始化失败: {e}")
    finally:
        conn.close()

def create_tables(cursor):
    """创建所有必要的表结构"""
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
    
    # 创建students表（如果不存在）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        student_id TEXT UNIQUE NOT NULL,
        enrollment_year INTEGER NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建teachers表（如果不存在）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        teacher_id TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建courses表（如果不存在）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        learn_time TEXT,
        credit REAL,
        usual_score INTEGER,
        midterm_score INTEGER,
        final_score INTEGER,
        times TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建student_courses表（如果不存在）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS student_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        course_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (course_id) REFERENCES courses (id),
        UNIQUE (student_id, course_id)
    )
    ''')
    
    # 创建teacher_courses表（如果不存在）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS teacher_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER,
        course_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES teachers (id),
        FOREIGN KEY (course_id) REFERENCES courses (id),
        UNIQUE (teacher_id, course_id)
    )
    ''')
    
    # 创建grades表（如果不存在）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        course_id INTEGER,
        usual_grade REAL,
        midterm_grade REAL,
        final_grade REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (course_id) REFERENCES courses (id),
        UNIQUE (student_id, course_id)
    )
    ''')
    
    # 创建assignments表（如果不存在）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        title TEXT NOT NULL,
        content TEXT,
        create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses (id)
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
            enrollment_year INTEGER NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        # 复制数据
        cursor.execute('''
        INSERT INTO students_temp (id, name, student_id, enrollment_year, created_at)
        SELECT id, name, student_id, enrollment_year, created_at FROM students
        ''')
        # 删除原表
        cursor.execute("DROP TABLE students")
        # 重命名临时表
        cursor.execute("ALTER TABLE students_temp RENAME TO students")

def add_test_data(cursor):
    """向各表中添加测试数据"""
    # 检查是否已存在测试数据
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        print("数据库中已有数据，跳过测试数据插入")
        return
    
    # 插入用户
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 添加管理员用户
    cursor.execute('''
    INSERT INTO users (username, password, role, created_at) 
    VALUES (?, ?, ?, ?)
    ''', ('admin', '123456', 'admin', current_time))
    admin_id = cursor.lastrowid
    
    # 添加教师用户
    cursor.execute('''
    INSERT INTO users (username, password, role, created_at)
    VALUES (?, ?, ?, ?)
    ''', ('teacher', '123456', 'teacher', current_time))
    teacher_id = cursor.lastrowid
    
    # 添加学生用户
    cursor.execute('''
    INSERT INTO users (username, password, role, created_at)
    VALUES (?, ?, ?, ?)
    ''', ('student', '123456', 'student', current_time))
    student_id = cursor.lastrowid
    
    # 添加管理员记录
    cursor.execute('''
    INSERT INTO admins (name, admin_id, created_at)
    VALUES (?, ?, ?)
    ''', ('admin', f'A{admin_id:04d}', current_time))
    
    # 添加教师记录
    cursor.execute('''
    INSERT INTO teachers (name, teacher_id, created_at)
    VALUES (?, ?, ?)
    ''', ('teacher', f'T{teacher_id:04d}', current_time))
    teacher_record_id = cursor.lastrowid
    
    # 添加学生记录
    cursor.execute('''
    INSERT INTO students (name, student_id, enrollment_year, created_at)
    VALUES (?, ?, ?, ?)
    ''', ('student', f'S{student_id:04d}', 2023, current_time))
    student_record_id = cursor.lastrowid
    
    # 添加课程
    cursor.execute('''
    INSERT INTO courses (name, learn_time, credit, usual_score, midterm_score, final_score, times)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('软件工程', '大三', 4.0, 30, 30, 40, '星期一 8:30-10:10|星期三 14:00-15:40'))
    course_id = cursor.lastrowid
    
    # 添加第二门课程
    cursor.execute('''
    INSERT INTO courses (name, learn_time, credit, usual_score, midterm_score, final_score, times)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('数据库原理', '大二', 3.0, 20, 30, 50, '星期二 10:20-12:00|星期四 15:50-17:30'))
    course_id2 = cursor.lastrowid
    
    # 添加教师课程关系
    cursor.execute('''
    INSERT INTO teacher_courses (teacher_id, course_id)
    VALUES (?, ?)
    ''', (teacher_record_id, course_id))
    
    cursor.execute('''
    INSERT INTO teacher_courses (teacher_id, course_id)
    VALUES (?, ?)
    ''', (teacher_record_id, course_id2))
    
    # 添加学生课程关系
    cursor.execute('''
    INSERT INTO student_courses (student_id, course_id)
    VALUES (?, ?)
    ''', (student_record_id, course_id))
    
    # 添加成绩记录
    cursor.execute('''
    INSERT INTO grades (student_id, course_id, usual_grade, midterm_grade, final_grade)
    VALUES (?, ?, ?, ?, ?)
    ''', (student_record_id, course_id, 85.0, 90.0, 88.0))
    
    # 添加作业记录
    cursor.execute('''
    INSERT INTO assignments (course_id, title, content)
    VALUES (?, ?, ?)
    ''', (course_id, '软件工程概论作业', '请阅读教材第一章，完成练习1-5。'))
    
    cursor.execute('''
    INSERT INTO assignments (course_id, title, content)
    VALUES (?, ?, ?)
    ''', (course_id, '软件设计模式作业', '分析并总结三种常用的设计模式，并举例说明其应用场景。'))
    
    cursor.execute('''
    INSERT INTO assignments (course_id, title, content)
    VALUES (?, ?, ?)
    ''', (course_id2, '数据库设计作业', '设计一个图书管理系统的数据库，包含至少5个表。'))
    
    print("测试数据插入完成")
    
    # 输出测试账号信息
    print("\n=== 测试账号信息 ===")
    print("管理员账号: admin / 123456")
    print("教师账号: teacher / 123456")
    print("学生账号: student / 123456")
    print("===================\n")
