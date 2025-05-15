import sqlite3
from py.config import DATABASE_PATH

def get_db_connection():
    """创建数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # 设置行工厂，使结果可以通过列名访问
    return conn

def execute_query(query, params=(), fetch_all=True):
    """执行查询并返回结果"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.fetchone()
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def execute_insert(query, params=()):
    """执行插入操作并返回新记录的ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        new_id = cursor.lastrowid
        conn.commit()
        return new_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def execute_update(query, params=()):
    """执行更新操作"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        affected_rows = cursor.rowcount
        conn.commit()
        return affected_rows
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def execute_delete(query, params=()):
    """执行删除操作"""
    return execute_update(query, params)

# 数据库操作函数
def add_record(table, data):
    """通用添加记录函数"""
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['?' for _ in data])
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    return execute_insert(query, tuple(data.values()))

def update_record(table, data, condition):
    """通用更新记录函数"""
    set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
    where_clause = ' AND '.join([f"{k} = ?" for k in condition.keys()])
    query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
    values = tuple(list(data.values()) + list(condition.values()))
    return execute_update(query, values)

def delete_record(table, condition):
    """通用删除记录函数"""
    where_clause = ' AND '.join([f"{k} = ?" for k in condition.keys()])
    query = f"DELETE FROM {table} WHERE {where_clause}"
    return execute_delete(query, tuple(condition.values()))

def get_records(table, condition=None):
    """通用获取记录函数"""
    query = f"SELECT * FROM {table}"
    params = ()
    if condition:
        where_clause = ' AND '.join([f"{k} = ?" for k in condition.keys()])
        query += f" WHERE {where_clause}"
        params = tuple(condition.values())
    return execute_query(query, params)

