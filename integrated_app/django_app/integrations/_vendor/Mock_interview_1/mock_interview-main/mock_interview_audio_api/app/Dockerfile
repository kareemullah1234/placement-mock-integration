# Use an official Python runtime as the base image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements first, to leverage Docker layer caching
COPY requirements.txt /app/

# Install necessary dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Install any additional dependencies your code might require
# RUN pip install <additional-packages>

# Expose the port if needed (not required for your script unless used in Flask or similar framework)
EXPOSE 5000

# Define the command to run your script
CMD ["python", "app.py"]
