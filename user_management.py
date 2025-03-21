import streamlit as st
import pandas as pd
import db

# 用户管理页面
def user_management_page():
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
                conn = db.get_db_connection()
                departments = pd.read_sql_query('SELECT DISTINCT department FROM users', conn)['department']
                conn.close()
                filter_department = st.selectbox('按部门筛选', ['全部'] + list(departments), key='filter_department')
            with filter_col3:
                filter_role = st.selectbox('按角色筛选', ['全部', 'admin', 'user'], key='filter_role')
        
        # 用户列表
        st.subheader('用户列表')
        users_df = db.get_all_users(search_name, filter_department, filter_role)
        
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
                    if st.button('编辑', key=f'edit_user_{row["username"]}_{index}'):
                        st.session_state['editing_user'] = row['username']
                        st.session_state['edit_name'] = row['name']
                        st.session_state['edit_department'] = row['department']
                        st.session_state['edit_position'] = row['position']
                        st.session_state['edit_employee_id'] = row['employee_id']
                        st.session_state['edit_role'] = row['role']
                with cols[5]:
                    if row['username'] != 'admin':
                        if st.button('删除', key=f'delete_{row["username"]}_{index}'):
                            if db.delete_user(row['username']):
                                st.success('用户删除成功')
                                st.rerun()
            st.divider()
        
        # 如果没有用户显示提示信息
        if len(users_df) == 0:
            st.info('没有找到符合条件的用户')
    
    with col2:
        # 判断是否处于编辑模式
        if 'editing_user' in st.session_state:
            # 编辑用户表单
            st.subheader('编辑用户')
            edit_name = st.text_input('姓名', value=st.session_state['edit_name'], key='edit_name_input')
            edit_department = st.text_input('部门', value=st.session_state['edit_department'], key='edit_department_input')
            edit_position = st.text_input('岗位', value=st.session_state['edit_position'], key='edit_position_input')
            edit_employee_id = st.text_input('工号', value=st.session_state['edit_employee_id'], key='edit_employee_id_input')
            edit_role = st.selectbox('角色', ['user', 'admin'], index=0 if st.session_state['edit_role'] == 'user' else 1, key='edit_role_input')
            edit_password = st.text_input('新密码 (留空不修改)', type='password', key='edit_password_input')
            
            col1_btn, col2_btn = st.columns(2)
            with col1_btn:
                if st.button('保存修改', key='save_edit_btn'):
                    if db.update_user(st.session_state['editing_user'], edit_name, edit_department, edit_position, edit_employee_id, edit_role, edit_password):
                        st.success('用户信息更新成功')
                        del st.session_state['editing_user']
                        st.rerun()
            
            with col2_btn:
                if st.button('取消', key='cancel_edit_btn'):
                    del st.session_state['editing_user']
                    st.rerun()
        else:
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
                    if db.add_user(new_username, new_name, new_password, new_role, new_department, new_position, new_employee_id):
                        st.success('用户添加成功')
                        st.rerun()
                else:
                    st.warning('请填写必要信息（用户名、姓名、密码）')