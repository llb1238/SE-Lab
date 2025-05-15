import sqlite3
from py.config import DATABASE_PATH
import time

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

# 修改添加记录函数，处理特殊情况下的字段缺失
def add_record(table, data_dict):
    """添加一条记录到指定表中，并返回新记录的ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 获取表结构信息
        cursor.execute(f"PRAGMA table_info({table})")
        table_info = cursor.fetchall()
        
        # 查找必需字段（具有NOT NULL约束且没有默认值的字段）
        required_fields = []
        for field in table_info:
            if field['notnull'] == 1 and field['dflt_value'] is None and field['name'] != 'id':
                required_fields.append(field['name'])
        
        # 检查是否所有必需字段都在data_dict中
        missing_fields = [f for f in required_fields if f not in data_dict]
        if missing_fields:
            # 特殊情况处理: enrollment_year
            if 'enrollment_year' in missing_fields and table == 'students':
                data_dict['enrollment_year'] = time.localtime().tm_year
                missing_fields.remove('enrollment_year')
            
            # 如果仍有缺失字段，抛出异常
            if missing_fields:
                raise ValueError(f"缺少必要字段: {', '.join(missing_fields)}")
        
        # 构建SQL语句
        fields = ', '.join(data_dict.keys())
        placeholders = ', '.join(['?'] * len(data_dict))
        sql = f"INSERT INTO {table} ({fields}) VALUES ({placeholders})"
        
        # 执行插入
        cursor.execute(sql, list(data_dict.values()))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        print(f"添加记录到{table}失败:", e)
        raise
    finally:
        conn.close()

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

