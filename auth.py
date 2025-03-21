import streamlit as st
import streamlit_authenticator as stauth
import db

# 用户认证函数
def authenticate():
    # 获取用户凭证
    credentials = db.get_credentials()
    
    # 配置认证器
    authenticator = stauth.Authenticate(
        credentials,
        'kpi_cookie',
        'kpi_key',
        cookie_expiry_days=30
    )
    
    # 登录界面
    name, authentication_status, username = authenticator.login('登录', location='main')
    
    # 处理登录状态
    if authentication_status == False:
        st.error('用户名或密码错误')
    elif authentication_status == None:
        st.warning('请输入用户名和密码')
    
    # 返回认证信息
    return authenticator, name, authentication_status, username

# 退出登录
def logout(authenticator):
    if st.sidebar.button('退出'):
        try:
            authenticator.cookie_manager.delete('kpi_cookie')
        except:
            pass
        st.session_state.clear()
        st.rerun()