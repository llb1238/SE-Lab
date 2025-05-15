import os
import sys
import sqlite3
import time

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from py.config import DATABASE_PATH

def init_db():
    """初始化数据库，创建必要的表并修复表结构"""
    # 确保数据库目录存在
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # 使查询结果可通过列名访问
    
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'student',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建学生表（enrollment_year可以为NULL）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        student_id TEXT UNIQUE NOT NULL,
        enrollment_year INTEGER
    )
    ''')

    # 检查现有表结构
    cursor.execute("PRAGMA table_info(students)")
    columns = cursor.fetchall()
    
    if columns:  # 如果students表已存在
        try:
            # 尝试从旧表复制数据到新表
            cursor.execute('''
            INSERT INTO students_new (id, name, student_id, enrollment_year)
            SELECT id, name, student_id, enrollment_year FROM students
            ''')
            print("成功从旧学生表复制数据")
        except Exception as e:
            print(f"复制学生数据出错: {e}")
        
        # 删除旧表
        cursor.execute("DROP TABLE students")
        print("删除旧学生表")
    
    # 重命名新表为students
    cursor.execute("ALTER TABLE students_new RENAME TO students")
    print("学生表更新完成")
    
    # 创建教师表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        teacher_id TEXT UNIQUE NOT NULL
    )
    ''')
    
    # 创建课程表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        learn_time TEXT,
        credit REAL NOT NULL,
        usual_score INTEGER NOT NULL,
        midterm_score INTEGER NOT NULL,
        final_score INTEGER NOT NULL,
        times TEXT
    )
    ''')
    
    # 创建学生选课表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS student_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (course_id) REFERENCES courses (id),
        UNIQUE(student_id, course_id)
    )
    ''')
    
    # 创建教师课程表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS teacher_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        FOREIGN KEY (teacher_id) REFERENCES teachers (id),
        FOREIGN KEY (course_id) REFERENCES courses (id),
        UNIQUE(teacher_id, course_id)
    )
    ''')
    
    # 创建成绩表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        usual_grade REAL,
        midterm_grade REAL,
        final_grade REAL,
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (course_id) REFERENCES courses (id),
        UNIQUE(student_id, course_id)
    )
    ''')
    
    # 创建作业表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT,
        create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    print("数据库初始化完成")

if __name__ == "__main__":
    print("开始初始化数据库...")
    init_db()
