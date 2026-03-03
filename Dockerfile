# Use the official Python slim image as the base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set the default command to run the bot. The bot reads the token from
# the environment variable TELEGRAM_TOKEN or uses the placeholder in code.
CMD ["python", "main.py"]