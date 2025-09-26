FROM python:3.12-slim

# Install system deps (needed for pyodbc)
RUN apt-get update && apt-get install -y \
    gcc g++ gnupg curl unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Install ODBC driver for SQL Server
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
      | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] \
      https://packages.microsoft.com/debian/12/prod bookworm main" \
      > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -U pip setuptools wheel
RUN pip install -e .[dev]

EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
