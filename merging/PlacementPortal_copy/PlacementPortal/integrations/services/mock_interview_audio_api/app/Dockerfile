# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install necessary dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install any additional dependencies your code might require
# RUN pip install <additional-packages>

# Expose the port if needed (not required for your script unless used in Flask or similar framework)
EXPOSE 5000

# Define the command to run your script
CMD ["python", "app.py"]
