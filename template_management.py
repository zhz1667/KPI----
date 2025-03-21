import streamlit as st
import pandas as pd
import db

# 考核模板管理页面
def template_management_page():
    st.title('考核模板')
    
    # 创建两列布局
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader('考核模板列表')
        templates_df = db.get_all_templates()
            
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
                        if delete_template(template['template_id']):
                            st.success('模板删除成功')
                            st.rerun()
                st.divider()
                
                # 显示模板的考核指标
                if 'viewing_template' in st.session_state and st.session_state['viewing_template'] == template['template_id']:
                    indicators_df = db.get_template_indicators(template['template_id'])
                    
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
        
        if templates_df.empty:
            st.info('暂无考核模板')
    
    with col2:
        st.subheader('新增考核模板')
        new_template_name = st.text_input('模板名称', key='new_template_name')
        new_template_desc = st.text_area('模板描述', key='new_template_desc')
        
        if st.button('创建模板'):
            if new_template_name:
                if create_template(new_template_name, new_template_desc):
                    st.success('模板创建成功')
                    st.rerun()
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
                    if add_indicator(st.session_state['editing_template'], new_indicator_seq, 
                                    new_indicator_category, new_indicator_name, new_indicator_desc,
                                    new_indicator_criteria, new_indicator_weight):
                        st.success('指标添加成功')
                        del st.session_state['editing_template']
                        st.rerun()
                else:
                    st.warning('请填写指标名称和权重')

# 编辑模板表单
def edit_template_form():
    if 'editing_template_info' in st.session_state:
        st.subheader('编辑模板')
        edit_template_name = st.text_input('模板名称', value=st.session_state['editing_template_info']['template_name'], key='edit_template_name')
        edit_template_desc = st.text_area('模板描述', value=st.session_state['editing_template_info']['description'], key='edit_template_desc')
        
        if st.button('保存修改'):
            if edit_template_name:
                if update_template(st.session_state['editing_template_info']['template_id'], edit_template_name, edit_template_desc):
                    st.success('模板修改成功')
                    del st.session_state['editing_template_info']
                    st.rerun()
            else:
                st.warning('请填写模板名称')
        
        if st.button('取消修改'):
            del st.session_state['editing_template_info']
            st.rerun()

# 创建模板
def create_template(template_name, description):
    try:
        conn = db.get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO kpi_templates (template_name, description) VALUES (?, ?)',
                (template_name, description))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f'创建模板失败: {str(e)}')
        return False

# 更新模板
def update_template(template_id, template_name, description):
    try:
        conn = db.get_db_connection()
        c = conn.cursor()
        c.execute('UPDATE kpi_templates SET template_name = ?, description = ? WHERE template_id = ?',
                (template_name, description, template_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f'修改模板失败: {str(e)}')
        return False

# 删除模板
def delete_template(template_id):
    try:
        conn = db.get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM kpi_indicators WHERE template_id = ?', (template_id,))
        c.execute('DELETE FROM kpi_templates WHERE template_id = ?', (template_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f'删除模板失败: {str(e)}')
        return False

# 添加指标
def add_indicator(template_id, sequence_number, category, name, description, evaluation_criteria, weight):
    try:
        conn = db.get_db_connection()
        c = conn.cursor()
        
        # 检查权重总和是否超过100%
        current_weight_sum = pd.read_sql_query(
            'SELECT SUM(weight) as total_weight FROM kpi_indicators WHERE template_id = ?',
            conn,
            params=(template_id,)
        )['total_weight'].iloc[0] or 0
        
        if current_weight_sum + weight <= 100:
            c.execute('''
                INSERT INTO kpi_indicators 
                (template_id, sequence_number, category, name, description, evaluation_criteria, weight)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (template_id, sequence_number, category, name, description, evaluation_criteria, weight))
            conn.commit()
            conn.close()
            return True
        else:
            st.error('指标权重总和不能超过100%')
            conn.close()
            return False
    except Exception as e:
        st.error(f'添加指标失败: {str(e)}')
        return False