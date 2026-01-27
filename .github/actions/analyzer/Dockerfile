FROM python:3.14-slim

# Claude CLI と Gemini CLI をインストール
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @anthropic-ai/claude-code @google/gemini-cli && \
    rm -rf /var/lib/apt/lists/*

COPY app /app/

WORKDIR /app
RUN pip install -r requirements.txt
RUN chmod +x /app/entrypoint.sh /app/vulnerability_analyzer.py

ENTRYPOINT ["/app/entrypoint.sh"]
