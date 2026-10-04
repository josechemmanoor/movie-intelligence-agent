import streamlit as st

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import MovieAgent
st.set_page_config(
    page_title="Movie Intelligence & Follow-up Assistant",
    page_icon="🎬",
    layout="wide",
)

@st.cache_resource
def get_agent():
    return MovieAgent()

st.title("🎬 Movie Intelligence & Follow-up Assistant")
st.caption("Subtitle RAG • Grounded citations • Agent routing • MCP email")

with st.sidebar:
    st.header("Setup")
    st.markdown(
        """
        **Informational query**
        > What does Cooper say about his father?

        **Email action**
        > Email a summary of the scene about Cooper's father to name@example.com.

        Add `.srt` files to `data/movies/` and build the index with:
        `python -m src.vector_store`
        """
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                for source in message["sources"]:
                    st.markdown(
                        f"**{source['citation']}**  \n"
                        f"{source['text']}"
                    )

query = st.chat_input("Ask about a movie or request an email...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Searching subtitles and reasoning..."):
            try:
                result = get_agent().handle(query)
                st.markdown(result.message)

                if result.sources:
                    with st.expander("Retrieved Sources"):
                        for source in result.sources:
                            st.markdown(
                                f"**{source['citation']}**  \n"
                                f"Similarity: {source['similarity']}  \n"
                                f"{source['text']}"
                            )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result.message,
                    "sources": result.sources,
                })
            except Exception as exc:
                error = f"Error: {exc}"
                st.error(error)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error,
                    "sources": [],
                })
