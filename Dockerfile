FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY krakow_air ./krakow_air
RUN pip install --no-cache-dir . && useradd --create-home app
USER app
ENTRYPOINT ["python", "-m", "krakow_air"]
