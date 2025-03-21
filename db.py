import sqlite3
import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth

# 数据库连接函数
def get_db_connection():
    try:
        conn = sqlite3.connect('kpi.db', timeout=30)
        conn.execute('PRAGMA journal_mode=WAL;')  # 使用预写日志模式
        
        # 执行完整性检查
        integrity_check = conn.execute('PRAGMA integrity_check;').fetchone()[0]
        if integrity_check != 'ok':
            raise sqlite3.DatabaseError(f'数据库完整性检查失败: {integrity_check}')
        
        return conn
    except sqlite3.Error as e:
        st.error(f'数据库连接错误: {str(e)}')
        st.error('建议操作: 1. 恢复备份数据库 2. 删除当前数据库重新初始化')
        raise

# 初始化数据库
def init_db():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # 创建用户表
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                name TEXT,
                password TEXT,
                role TEXT,
                department TEXT,
                position TEXT,
                employee_id TEXT
            )
        ''')
        
        # 创建考核模板表
        c.execute('''
            CREATE TABLE IF NOT EXISTS kpi_templates (
                template_id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建考核指标表
        c.execute('''
            CREATE TABLE IF NOT EXISTS kpi_indicators (
                indicator_id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER,
                sequence_number INTEGER,
                category TEXT,
                name TEXT NOT NULL,
                description TEXT,
                evaluation_criteria TEXT,
                weight DECIMAL(5,2),
                FOREIGN KEY (template_id) REFERENCES kpi_templates (template_id)
            )
        ''')
        
        # 检查默认用户
        c.execute('SELECT * FROM users WHERE username = ?', ('admin',))
        if not c.fetchone():
            hashed_password = stauth.Hasher(['admin']).generate()[0]
            c.execute('''
                INSERT INTO users 
                (username, name, password, role, department, position, employee_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('admin', 'Administrator', hashed_password, 'admin', '管理部', '系统管理员', 'ADMIN001'))
        
        conn.commit()
    
    except sqlite3.Error as e:
        st.error(f'数据库错误: {str(e)}')
        st.error('建议操作: 1. 恢复备份数据库 2. 删除当前数据库重新初始化')
        raise
    finally:
        if 'conn' in locals():
            conn.close()

# 获取所有用户
def get_all_users(search_name="", filter_department="全部", filter_role="全部"):
    conn = get_db_connection()
    users_df = pd.read_sql_query('SELECT username, name, role, department, position, employee_id FROM users', conn)
    conn.close()
    
    # 应用筛选条件
    if search_name:
        users_df = users_df[users_df['name'].str.contains(search_name, na=False)]
    if filter_department != '全部':
        users_df = users_df[users_df['department'] == filter_department]
    if filter_role != '全部':
        users_df = users_df[users_df['role'] == filter_role]
    
    return users_df

# 添加新用户
def add_user(username, name, password, role, department, position, employee_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # 检查用户名是否已存在
        c.execute('SELECT username FROM users WHERE username = ?', (username,))
        if c.fetchone() is not None:
            st.error('用户名已存在')
            conn.close()
            return False
        
        # 添加新用户
        hashed_password = stauth.Hasher([password]).generate()[0]
        c.execute('INSERT INTO users (username, name, password, role, department, position, employee_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (username, name, hashed_password, role, department, position, employee_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f'添加用户失败: {str(e)}')
        return False

# 更新用户信息
def update_user(username, name, department, position, employee_id, role, password=None):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        if password and password.strip():
            # 更新包括密码
            hashed_password = stauth.Hasher([password]).generate()[0]
            c.execute('''
                UPDATE users 
                SET name = ?, department = ?, position = ?, employee_id = ?, role = ?, password = ? 
                WHERE username = ?
            ''', (name, department, position, employee_id, role, hashed_password, username))
        else:
            # 不更新密码
            c.execute('''
                UPDATE users 
                SET name = ?, department = ?, position = ?, employee_id = ?, role = ? 
                WHERE username = ?
            ''', (name, department, position, employee_id, role, username))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f'更新用户失败: {str(e)}')
        return False

# 删除用户
def delete_user(username):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE username = ?', (username,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f'删除用户失败: {str(e)}')
        return False

# 获取用户凭证
def get_credentials():
    conn = get_db_connection()
    users_df = pd.read_sql_query('SELECT * FROM users', conn)
    conn.close()
    
    credentials = {
        'usernames': {}
    }
    
    for _, row in users_df.iterrows():
        credentials['usernames'][row['username']] = {
            'name': row['name'],
            'password': row['password'],
            'role': row['role']
        }
    
    return credentials

# 获取所有模板
def get_all_templates():
    conn = get_db_connection()
    templates_df = pd.read_sql_query('SELECT * FROM kpi_templates', conn)
    conn.close()
    return templates_df

# 获取模板的指标
def get_template_indicators(template_id):
    conn = get_db_connection()
    indicators_df = pd.read_sql_query(
        'SELECT * FROM kpi_indicators WHERE template_id = ? ORDER BY sequence_number',
        conn,
        params=(template_id,)
    )
    conn.close()
    return indicators_df