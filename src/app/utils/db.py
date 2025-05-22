import sqlite3
import os
import time
from app.config import DATABASE_PATH

def get_db_connection():
    """获取数据库连接"""
    # 确保数据库目录存在
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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

def update_record(table, id, data):
    """更新记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE id = ?"
        cursor.execute(sql, tuple(data.values()) + (id,))
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        conn.rollback()
        print(f"更新记录失败: {e}")
        return None
    finally:
        conn.close()

def delete_record(table, id):
    """删除记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = f"DELETE FROM {table} WHERE id = ?"
        cursor.execute(sql, (id,))
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        conn.rollback()
        print(f"删除记录失败: {e}")
        return None
    finally:
        conn.close()

def get_records(table, conditions=None):
    """获取记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = f"SELECT * FROM {table}"
        if conditions:
            where_clause = ' AND '.join([f"{key} = ?" for key in conditions.keys()])
            sql += f" WHERE {where_clause}"
            cursor.execute(sql, tuple(conditions.values()))
        else:
            cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"获取记录失败: {e}")
        return []
    finally:
        conn.close()