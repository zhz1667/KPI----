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
            role TEXT,
            department TEXT,
            position TEXT,
            employee_id TEXT
        )
    ''')
    
    # 检查是否已存在admin用户
    c.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not c.fetchone():
        # 创建默认管理员账户
        hashed_password = stauth.Hasher(['admin']).generate()[0]
        c.execute('INSERT INTO users (username, name, password, role, department, position, employee_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                ('admin', 'Administrator', hashed_password, 'admin', '管理部', '系统管理员', 'ADMIN001'))
    
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
            # 在侧边栏添加导航菜单
            st.sidebar.title('系统管理')
            menu_selection = st.sidebar.radio('', ['用户管理'])
            
            if menu_selection == '用户管理':
                # 创建两列布局
                col1, col2 = st.columns([2, 1])
            
            # 添加筛选功能
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            with filter_col1:
                search_name = st.text_input('按姓名搜索', key='search_name')
            with filter_col2:
                filter_department = st.selectbox('按部门筛选', ['全部'] + list(pd.read_sql_query('SELECT DISTINCT department FROM users', sqlite3.connect('kpi.db'))['department']), key='filter_department')
            with filter_col3:
                filter_role = st.selectbox('按角色筛选', ['全部', 'admin', 'user'], key='filter_role')
            
            with col1:
                # 用户列表
                st.subheader('用户列表')
                conn = sqlite3.connect('kpi.db')
                users_df = pd.read_sql_query('SELECT username, name, role, department, position, employee_id FROM users', conn)
                conn.close()
                
                # 应用筛选条件
                if search_name:
                    users_df = users_df[users_df['name'].str.contains(search_name, na=False)]
                if filter_department != '全部':
                    users_df = users_df[users_df['department'] == filter_department]
                if filter_role != '全部':
                    users_df = users_df[users_df['role'] == filter_role]
                
                # 为每个用户添加操作按钮
                for index, row in users_df.iterrows():
                    with st.expander(f"👤 {row['name']} - {row['department']} ({row['position']})"): 
                        st.write(f"工号: {row['employee_id']}")
                        st.write(f"用户名: {row['username']}")
                        st.write(f"角色: {row['role']}")
                        
                        # 编辑和删除按钮
                        col_edit, col_delete = st.columns(2)
                        with col_edit:
                            if st.button('编辑', key=f'edit_{row["username"]}'):
                                st.session_state['editing_user'] = row['username']
                                st.session_state['edit_name'] = row['name']
                                st.session_state['edit_department'] = row['department']
                                st.session_state['edit_position'] = row['position']
                                st.session_state['edit_employee_id'] = row['employee_id']
                                st.session_state['edit_role'] = row['role']
                        
                        with col_delete:
                            if row['username'] != 'admin':
                                if st.button('删除', key=f'delete_{row["username"]}'):
                                    conn = sqlite3.connect('kpi.db')
                                    c = conn.cursor()
                                    c.execute('DELETE FROM users WHERE username = ?', (row['username'],))
                                    conn.commit()
                                    conn.close()
                                    st.success('用户删除成功')
                                    st.rerun()
                            else:
                                st.write('系统管理员不可删除')
                
                # 如果没有用户显示提示信息
                if len(users_df) == 0:
                    st.info('没有找到符合条件的用户')
            
            with col2:
                # 新增用户表单
                st.subheader('新增用户')
                new_username = st.text_input('用户名', key='new_username')
                new_name = st.text_input('姓名', key='new_name')
                new_password = st.text_input('密码', type='password', key='new_password')
                new_role = st.selectbox('角色', ['user', 'admin'], key='new_role')
                new_department = st.text_input('部门', key='new_department')
                new_position = st.text_input('岗位', key='new_position')
                new_employee_id = st.text_input('工号', key='new_employee_id')
                
                if st.button('添加用户'):
                    if new_username and new_name and new_password:
                        try:
                            conn = sqlite3.connect('kpi.db')
                            c = conn.cursor()
                            
                            # 检查用户名是否已存在
                            c.execute('SELECT username FROM users WHERE username = ?', (new_username,))
                            if c.fetchone() is not None:
                                st.error('用户名已存在')
                            else:
                                # 添加新用户
                                hashed_password = stauth.Hasher([new_password]).generate()[0]
                                c.execute('INSERT INTO users (username, name, password, role, department, position, employee_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                        (new_username, new_name, hashed_password, new_role, new_department, new_position, new_employee_id))
                                conn.commit()
                                st.success('用户添加成功')
                                st.rerun()
                            
                            conn.close()
                        except Exception as e:
                            st.error(f'添加用户失败: {str(e)}')
                    else:
                        st.warning('请填写必要信息（用户名、姓名、密码）')

        else:
            st.title('KPI考核系统')
            st.info('普通用户功能开发中...')

if __name__ == '__main__':
    main()