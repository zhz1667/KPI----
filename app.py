import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import sqlite3
from pathlib import Path
import pandas as pd

# 初始化数据库
def init_db():
    conn = sqlite3.connect('kpi.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            name TEXT,
            password TEXT,
            role TEXT
        )
    ''')
    
    # 检查是否已存在admin用户
    c.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not c.fetchone():
        # 创建默认管理员账户
        hashed_password = stauth.Hasher(['admin']).generate()[0]
        c.execute('INSERT INTO users (username, name, password, role) VALUES (?, ?, ?, ?)',
                ('admin', 'Administrator', hashed_password, 'admin'))
    
    conn.commit()
    conn.close()

# 获取用户凭证
def get_credentials():
    conn = sqlite3.connect('kpi.db')
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

# 主应用
def main():
    st.set_page_config(page_title='KPI考核系统', layout='wide')
    
    # 初始化数据库
    init_db()
    
    # 配置认证器
    credentials = get_credentials()
    authenticator = stauth.Authenticate(
        credentials,
        'kpi_cookie',
        'kpi_key',
        cookie_expiry_days=30
    )
    
    # 登录界面
    name, authentication_status, username = authenticator.login('登录', location='main')
    
    if authentication_status == False:
        st.error('用户名或密码错误')
    elif authentication_status == None:
        st.warning('请输入用户名和密码')
    else:
        # 登录成功
        # 检查Cookie状态并处理退出逻辑
        if st.sidebar.button('退出'):
            try:
                authenticator.cookie_manager.delete('kpi_cookie')
            except:
                pass
            st.session_state.clear()
            st.rerun()
        st.sidebar.title(f'欢迎, {name}')
        
        # 根据用户角色显示不同功能
        user_role = credentials['usernames'][username]['role']
        
        if user_role == 'admin':
            st.title('系统管理')
            # 这里后续可以添加用户管理等功能
            st.info('管理员功能开发中...')
        else:
            st.title('KPI考核系统')
            st.info('普通用户功能开发中...')

if __name__ == '__main__':
    main()