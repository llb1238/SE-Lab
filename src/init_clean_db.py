import sqlite3
import os

def clean_database():
    """清空数据库中所有表的数据"""
    
    # 数据库文件路径 - 修复路径问题
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'edu_system.db')
    
    if not os.path.exists(db_path):
        print("数据库文件不存在，无需清理")
        return
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("开始清理数据库...")
        
        # 禁用外键约束检查
        cursor.execute('PRAGMA foreign_keys = OFF')
        
        # 清空所有表的数据（按依赖关系顺序）
        tables_to_clean = [
            'grades',           # 成绩表
            'assignments',      # 作业表
            'student_courses',  # 学生选课关系表
            'teacher_courses',  # 教师课程关系表
            'courses',          # 课程表
            'students',         # 学生表
            'teachers',         # 教师表
            'admins',           # 管理员表
            'users'             # 用户表
        ]
        
        for table in tables_to_clean:
            try:
                cursor.execute(f'DELETE FROM {table}')
                affected_rows = cursor.rowcount
                print(f"已清空表 {table}，删除了 {affected_rows} 条记录")
            except sqlite3.Error as e:
                print(f"清空表 {table} 时出错: {e}")
        
        # 清空sqlite_sequence表内容（重置自增ID）
        try:
            cursor.execute("DELETE FROM sqlite_sequence")
            print("已清空 sqlite_sequence 表，自增ID已重置")
        except sqlite3.Error as e:
            print(f"清空 sqlite_sequence 表时出错: {e}")
        
        # 重新启用外键约束检查
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # 提交更改
        conn.commit()
        print("\n数据库清理完成！所有表数据已删除，自增ID已重置。")
        
        # 验证清理结果
        print("\n验证清理结果：")
        for table in tables_to_clean:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                print(f"表 {table} 当前记录数: {count}")
            except sqlite3.Error as e:
                print(f"查询表 {table} 时出错: {e}")
                
        # 检查sqlite_sequence表记录数
        try:
            cursor.execute("SELECT COUNT(*) FROM sqlite_sequence")
            count = cursor.fetchone()[0]
            print(f"sqlite_sequence 表记录数: {count}")
        except sqlite3.Error as e:
            print(f"查询 sqlite_sequence 表时出错: {e}")
        
    except sqlite3.Error as e:
        print(f"数据库操作出错: {e}")
        if conn:
            conn.rollback()
    
    finally:
        if conn:
            conn.close()
            print("\n数据库连接已关闭")

def confirm_clean():
    """确认是否要清理数据库"""
    print("=" * 50)
    print("数据库清理工具")
    print("=" * 50)
    print("警告：此操作将删除数据库中的所有数据！")
    print("包括：用户、学生、教师、课程、成绩、作业等所有信息")
    print("此操作不可逆转！")
    print("=" * 50)
    
    while True:
        choice = input("确定要继续吗？(输入 'YES' 确认，其他任意键取消): ").strip()
        
        if choice == 'YES':
            print("\n开始清理数据库...")
            clean_database()
            break
        else:
            print("操作已取消")
            break

if __name__ == '__main__':
    confirm_clean()
