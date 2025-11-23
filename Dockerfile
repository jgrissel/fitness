# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8501 available to the world outside this container (for Streamlit)
EXPOSE 8501

# Define environment variable
ENV PYTHONUNBUFFERED=1

# The command to run will be overridden by Cloud Run Job or Service
# Default to dashboard for Service
CMD ["streamlit", "run", "dashboard.py", "--server.port=8080", "--server.address=0.0.0.0"]
