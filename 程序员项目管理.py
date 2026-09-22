# app.py
import streamlit as st
from supabase import create_client

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

if "user" not in st.session_state:
    st.title("🔐 登录")
    with st.form("login_form"):
        email = st.text_input("邮箱")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录", use_container_width=True)

    if submitted:
        try:
            client = create_client(url, key)
            res = client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            st.session_state["user"] = res.user
            st.session_state["access_token"] = res.session.access_token
            st.session_state["refresh_token"] = res.session.refresh_token
            st.rerun()
        except Exception as e:
            st.error(f"登录失败：{e}")
    st.stop()

# 登录后
st.title("📊 项目管理系统")
st.caption(f"当前用户：{st.session_state['user'].email}")

if st.button("退出登录"):
    for key in ("user", "access_token", "refresh_token"):
        st.session_state.pop(key, None)
    st.rerun()

st.markdown("""
欢迎使用！请通过左侧导航进入各个功能页面：

| 页面 | 功能 |
|------|------|
| 📝 **项目录入** | 录入 / 编辑 / 删除项目基础信息 |
| 📤 **LOT 上传与管理** | 上传项目的 LOT Excel（含 Datasets / TFLs） |
| 📊 **汇总视图** | 合并查看所有项目的 Datasets 和 TFLs |
| ⚙️ **BatchRun 生成** | 按条件生成 batchrun 脚本并下载 |
""")

st.info("💡 首次使用请先到「📝 项目录入」页面创建项目。")