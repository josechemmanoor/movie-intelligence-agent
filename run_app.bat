@echo off
python -m src.vector_store
streamlit run src/app.py
pause
