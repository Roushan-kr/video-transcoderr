FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .

# run at build proc
RUN pip install --no-cache-dir -r requirements.txt
COPY . .    

EXPOSE 8000

# run when container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]