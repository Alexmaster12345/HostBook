FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
RUN mkdir -p db

ENV DATABASE_URL=sqlite:///./db/hostbook.db
ENV SECRET_KEY=changeme
ENV AGENT_TOKEN=changeme-agent-secret

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
