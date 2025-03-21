import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import sqlite3
from pathlib import Path
import pandas as pd

# 初始化数据库
def init_db():
    try:
        # 添加数据库连接配置
        conn = sqlite3.connect('kpi.db', timeout=30)
        conn.execute('PRAGMA journal_mode=WAL;')  # 使用预写日志模式
        
        # 执行完整性检查
        integrity_check = conn.execute('PRAGMA integrity_check;').fetchone()[0]
        if integrity_check != 'ok':
            raise sqlite3.DatabaseError(f'数据库完整性检查失败: {integrity_check}')
            
        c = conn.cursor()
        
        # 原有建表语句保持不变...
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
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS kpi_templates (
                template_id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
            menu_selection = st.sidebar.radio('', ['用户管理', '考核模板'])
            
            # 初始化筛选变量
            search_name = ""
            filter_department = "全部"
            filter_role = "全部"
            
            if menu_selection == '用户管理':
                st.title('用户管理')
                
                # 创建两列布局
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # 添加筛选功能到一个容器中
                    with st.container():
                        st.subheader('筛选条件')
                        filter_col1, filter_col2, filter_col3 = st.columns(3)
                        with filter_col1:
                            search_name = st.text_input('按姓名搜索', key='search_name')
                        with filter_col2:
                            filter_department = st.selectbox('按部门筛选', ['全部'] + list(pd.read_sql_query('SELECT DISTINCT department FROM users', sqlite3.connect('kpi.db'))['department']), key='filter_department')
                        with filter_col3:
                            filter_role = st.selectbox('按角色筛选', ['全部', 'admin', 'user'], key='filter_role')
                    
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
                
                # 使用表格展示用户列表
                for index, row in users_df.iterrows():
                    with st.container():
                        cols = st.columns([1, 1, 1, 1, 1, 1])
                        with cols[0]:
                            st.write(f"👤 {row['name']}")
                        with cols[1]:
                            st.write(f"部门: {row['department']}")
                        with cols[2]:
                            st.write(f"职位: {row['position']}")
                        with cols[3]:
                            st.write(f"工号: {row['employee_id']}")
                        with cols[4]:
                            if st.button('编辑', key=f'edit_user_{row["username"]}_{index}_{pd.Timestamp.now().timestamp():.0f}'):
                                st.session_state['editing_user'] = row['username']
                                st.session_state['edit_name'] = row['name']
                                st.session_state['edit_department'] = row['department']
                                st.session_state['edit_position'] = row['position']
                                st.session_state['edit_employee_id'] = row['employee_id']
                                st.session_state['edit_role'] = row['role']
                        with cols[5]:
                            if row['username'] != 'admin':
                                if st.button('删除', key=f'delete_{row["username"]}_{index}_{pd.Timestamp.now().timestamp():.0f}'):
                                    conn = sqlite3.connect('kpi.db')
                                    c = conn.cursor()
                                    c.execute('DELETE FROM users WHERE username = ?', (row['username'],))
                                    conn.commit()
                                    conn.close()
                                    st.success('用户删除成功')
                                    st.rerun()
                    st.divider()
                
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
            
        elif menu_selection == '考核模板':
            st.title('考核模板')
            
            # 创建两列布局
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader('考核模板列表')
                conn = sqlite3.connect('kpi.db')
                templates_df = pd.read_sql_query('SELECT * FROM kpi_templates', conn)
                    
                for _, template in templates_df.iterrows():
                    with st.container():
                        cols = st.columns([2, 1, 1, 1])
                        with cols[0]:
                            st.write(f"📋 {template['template_name']}")
                            st.caption(f"描述: {template['description']}")
                        with cols[1]:
                            if st.button('查看指标', key=f"view_indicator_{template['template_id']}"):
                                st.session_state['viewing_template'] = template['template_id']
                        with cols[2]:
                            if st.button('编辑', key=f"edit_template_{template['template_id']}"):
                                st.session_state['editing_template_info'] = {
                                    'template_id': template['template_id'],
                                    'template_name': template['template_name'],
                                    'description': template['description']
                                }
                        with cols[3]:
                            if st.button('删除', key=f"delete_template_{template['template_id']}"):
                                conn = sqlite3.connect('kpi.db')
                                c = conn.cursor()
                                c.execute('DELETE FROM kpi_indicators WHERE template_id = ?', (template['template_id'],))
                                c.execute('DELETE FROM kpi_templates WHERE template_id = ?', (template['template_id'],))
                                conn.commit()
                                conn.close()
                                st.success('模板删除成功')
                                st.rerun()
                            st.divider()
                            
                            # 显示模板的考核指标
                            if 'viewing_template' in st.session_state and st.session_state['viewing_template'] == template['template_id']:
                                indicators_df = pd.read_sql_query(
                                    'SELECT * FROM kpi_indicators WHERE template_id = ? ORDER BY sequence_number',
                                    conn,
                                    params=(template['template_id'],)
                                )
                                
                                if not indicators_df.empty:
                                    st.write('考核指标:')
                                    for _, indicator in indicators_df.iterrows():
                                        with st.container():
                                            ind_cols = st.columns([1, 2, 2, 1])
                                            with ind_cols[0]:
                                                st.write(f"序号: {indicator['sequence_number']}")
                                                st.write(f"分类: {indicator['category']}")
                                            with ind_cols[1]:
                                                st.write(f"指标名称: {indicator['name']}")
                                                st.write(f"指标解释: {indicator['description']}")
                                            with ind_cols[2]:
                                                st.write(f"评价标准: {indicator['evaluation_criteria']}")
                                            with ind_cols[3]:
                                                st.write(f"权重: {indicator['weight']}%")
                                            st.divider()
                                
                                if st.button('添加指标', key=f"add_indicator_{template['template_id']}"):
                                    st.session_state['editing_template'] = template['template_id']
                    
                    conn.close()
                    
                    if templates_df.empty:
                        st.info('暂无考核模板')
                
                with col2:
                    st.subheader('新增考核模板')
                    new_template_name = st.text_input('模板名称', key='new_template_name')
                    new_template_desc = st.text_area('模板描述', key='new_template_desc')
                    
                    if st.button('创建模板'):
                        if new_template_name:
                            try:
                                conn = sqlite3.connect('kpi.db')
                                c = conn.cursor()
                                c.execute('INSERT INTO kpi_templates (template_name, description) VALUES (?, ?)',
                                        (new_template_name, new_template_desc))
                                conn.commit()
                                conn.close()
                                st.success('模板创建成功')
                                st.rerun()
                            except Exception as e:
                                st.error(f'创建模板失败: {str(e)}')
                        else:
                            st.warning('请填写模板名称')
                    
                    # 添加指标表单
                    if 'editing_template' in st.session_state:
                        st.subheader('添加考核指标')
                        new_indicator_seq = st.number_input('序号', min_value=1, value=1)
                        new_indicator_category = st.text_input('指标分类')
                        new_indicator_name = st.text_input('指标名称')
                        new_indicator_desc = st.text_area('指标解释')
                        new_indicator_criteria = st.text_area('评价标准')
                        new_indicator_weight = st.number_input('指标权重(%)', min_value=0.0, max_value=100.0, value=0.0)
                        
                        if st.button('保存指标'):
                            if new_indicator_name and new_indicator_weight:
                                try:
                                    conn = sqlite3.connect('kpi.db')
                                    c = conn.cursor()
                                    
                                    # 检查权重总和是否超过100%
                                    current_weight_sum = pd.read_sql_query(
                                        'SELECT SUM(weight) as total_weight FROM kpi_indicators WHERE template_id = ?',
                                        conn,
                                        params=(st.session_state['editing_template'],)
                                    )['total_weight'].iloc[0] or 0
                                    
                                    if current_weight_sum + new_indicator_weight <= 100:
                                        c.execute('''
                                            INSERT INTO kpi_indicators 
                                            (template_id, sequence_number, category, name, description, evaluation_criteria, weight)
                                            VALUES (?, ?, ?, ?, ?, ?, ?)
                                        ''', (st.session_state['editing_template'], new_indicator_seq,
                                              new_indicator_category, new_indicator_name, new_indicator_desc,
                                              new_indicator_criteria, new_indicator_weight))
                                        conn.commit()
                                        st.success('指标添加成功')
                                        del st.session_state['editing_template']
                                        st.rerun()
                                    else:
                                        st.error('指标权重总和不能超过100%')
                                    
                                    conn.close()
                                except Exception as e:
                                    st.error(f'添加指标失败: {str(e)}')
                            else:
                                st.warning('请填写指标名称和权重')
            
            
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
                            if st.button('编辑', key=f'edit_user_{row["username"]}'):
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
                new_username = st.text_input('用户名', key='add_user_username')
                new_name = st.text_input('姓名', key='add_user_name')
                new_password = st.text_input('密码', type='password', key='add_user_password')
                new_role = st.selectbox('角色', ['user', 'admin'], key='add_user_role')
                new_department = st.text_input('部门', key='add_user_department')
                new_position = st.text_input('岗位', key='add_user_position')
                new_employee_id = st.text_input('工号', key='add_user_employee_id')
                
                if st.button('添加用户', key='add_user_btn'):
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


# 编辑模板表单
if 'editing_template_info' in st.session_state:
    st.subheader('编辑模板')
    edit_template_name = st.text_input('模板名称', value=st.session_state['editing_template_info']['template_name'], key='edit_template_name')
    edit_template_desc = st.text_area('模板描述', value=st.session_state['editing_template_info']['description'], key='edit_template_desc')
    
    if st.button('保存修改'):
        if edit_template_name:
            try:
                conn = sqlite3.connect('kpi.db')
                c = conn.cursor()
                c.execute('UPDATE kpi_templates SET template_name = ?, description = ? WHERE template_id = ?',
                        (edit_template_name, edit_template_desc, st.session_state['editing_template_info']['template_id']))
                conn.commit()
                conn.close()
                st.success('模板修改成功')
                del st.session_state['editing_template_info']
                st.rerun()
            except Exception as e:
                st.error(f'修改模板失败: {str(e)}')
        else:
            st.warning('请填写模板名称')
    
    if st.button('取消修改'):
        del st.session_state['editing_template_info']
        st.rerun()