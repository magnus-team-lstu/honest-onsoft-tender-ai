from __future__ import annotations

import streamlit as st

from design.copy import SIDEBAR_BODY, SIDEBAR_FOOTER, SIDEBAR_TITLE
from design.paths import logo_path


def render_sidebar() -> None:
    logo = logo_path()
    with st.sidebar:
        if logo.is_file():
            st.image(str(logo), width="stretch")
        st.title(SIDEBAR_TITLE)
        st.markdown(SIDEBAR_BODY)
        st.divider()
        st.caption(SIDEBAR_FOOTER)
