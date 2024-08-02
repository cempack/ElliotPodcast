# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt ./

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expose port 8000 for the application
EXPOSE 8000

# Run the application using Gunicorn, pointing to the module and app object
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "120", "app:create_app()"]
