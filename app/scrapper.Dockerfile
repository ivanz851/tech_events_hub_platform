FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.8.3

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

COPY src/ ./src/
COPY migrations/ ./migrations/

EXPOSE 8080 9001

CMD ["python", "-m", "src.scrapper.server"]
