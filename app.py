import streamlit as st
import auth
import db
import user_management
import template_management

# 主应用
def main():
    st.set_page_config(page_title='KPI考核系统', layout='wide')
    
    # 初始化数据库
    db.init_db()
    
    # 用户认证
    authenticator, name, authentication_status, username = auth.authenticate()
    
    if authentication_status:
        # 登录成功
        # 处理退出登录
        auth.logout(authenticator)
        st.sidebar.title(f'欢迎, {name}')
        
        # 获取用户凭证
        credentials = db.get_credentials()
        user_role = credentials['usernames'][username]['role']
        
        if user_role == 'admin':
            # 在侧边栏添加导航菜单
            st.sidebar.title('系统管理')
            menu_selection = st.sidebar.radio('', ['用户管理', '考核模板'])
            
            if menu_selection == '用户管理':
                user_management.user_management_page()
            elif menu_selection == '考核模板':
                template_management.template_management_page()
                # 编辑模板表单
                template_management.edit_template_form()
        else:
            st.title('KPI考核系统')
            st.info('普通用户功能开发中...')

if __name__ == '__main__':
    main()