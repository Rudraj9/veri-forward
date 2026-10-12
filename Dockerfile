FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
ENV PATH=/home/user/.local/bin:$PATH PYTHONUNBUFFERED=1 HF_HOME=/home/user/.cache/huggingface
WORKDIR /home/user/app
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user:user . .
EXPOSE 7860
CMD ["python", "-m", "streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=7860", "--server.headless=true", "--server.maxUploadSize=5"]
