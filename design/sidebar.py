import streamlit as st
from pathlib import Path
import design.copy as copy

def render_sidebar():
    with st.sidebar:
        # 1. Логотип
        logo_path = Path(__file__).parent / "assets" / "logo.jpg"
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
        
        # 2. Тексты
        st.title(copy.SIDEBAR_TITLE)
        st.markdown(copy.SIDEBAR_TASK)
        st.markdown(copy.SIDEBAR_FORMULA)
        st.markdown(copy.SIDEBAR_TEAM)
        
        st.divider()
        st.caption(copy.SIDEBAR_FOOTER)