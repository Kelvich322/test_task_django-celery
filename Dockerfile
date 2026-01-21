FROM python:3.12

WORKDIR /app

RUN apt-get update && apt-get install -y zlib1g-dev make

RUN pip install uv

COPY uv.lock pyproject.toml ./

RUN uv pip install --system -r pyproject.toml

COPY . .

CMD ["sh", "-c", "cd /app/src && gunicorn --bind 0.0.0.0:8000 --workers 4 core.wsgi:application"]