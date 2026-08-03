# Everything the lab needs on the machine running the notebooks:
# Python, uv, and the Microsoft ODBC driver that pyodbc and dbt talk to
# SQL Server with. bookworm pinned: matches the Debian-12 ODBC repo below,
# and keeps the docker-in-docker feature on a supported base.
FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
