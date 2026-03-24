##
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Standard package installations
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    software-properties-common \
    gnupg2 \
    unixodbc-dev \
    build-essential

# MSSQL ODBC driver installation
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list \
    -o /etc/apt/sources.list.d/mssql-release.list

RUN apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18

ENV PATH="$PATH:/opt/mssql-tools18/bin"

# Python installation and setup
RUN apt-get install -y python3 python3-pip python3-dev

# Set working directory inside the container
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files into /app
COPY . .

# NOTE: The PYTHONPATH setting is usually not needed when using WORKDIR /app
# ENV PYTHONPATH=/app 

EXPOSE 8000

# *** FIX IS HERE ***: Change to reference main:app based on your file structure
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


##---------------------------------------------------------------------------##
# FROM python:3.10-slim

# WORKDIR /app

# RUN apt-get update && apt-get install -y build-essential

# COPY requirements.txt .

# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# EXPOSE 8000

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

##--------------------------------------------------------------------------------##

# FROM ubuntu:22.04

# ENV DEBIAN_FRONTEND=noninteractive

# RUN apt-get update && apt-get install -y \
#     curl \
#     apt-transport-https \
#     software-properties-common \
#     gnupg2 \
#     unixodbc-dev \
#     build-essential

# RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
# RUN curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list \
#     -o /etc/apt/sources.list.d/mssql-release.list

# RUN apt-get update && \
#     ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18

# ENV PATH="$PATH:/opt/mssql-tools18/bin"

# RUN apt-get install -y python3 python3-pip python3-dev

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

#ENV PYTHONPATH=/app

# # Ensure Python can import /app/backend
# ENV PYTHONPATH=/app

# EXPOSE 8000

# CMD ["uvicorn", "backend.fastapi_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
