# Use the official Python image from the Docker Hub
FROM python:3.10

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . /app/

# Expose port 8000 to allow external access
EXPOSE 8000

# Command to run the server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "myproj.wsgi:application"]
