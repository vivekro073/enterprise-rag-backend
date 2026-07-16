# 1. Use the official lightweight Python image
FROM python:3.10-slim

# 2. Hugging Face security requirement: Create a non-root user with ID 1000
RUN useradd -m -u 1000 user

# 3. Set environment variables to keep Python logs clean
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/user/.local/bin:$PATH"

# 4. Set the working directory inside the container
WORKDIR /home/user/app

# 5. Grant the user permission to create folders (Crucial for your PDF 'upload' dir)
RUN chown -R user:user /home/user/app

# 6. Switch to the new non-root user
USER user

# 7. Copy your requirements file first to cache the installations
COPY --chown=user:user requirements.txt .

# 8. Install the Python libraries
RUN pip install --no-cache-dir -r requirements.txt

# 9. Copy the rest of your backend code into the container
COPY --chown=user:user . .

# 10. Hugging Face routes all traffic to port 7860
EXPOSE 7860

# 11. Start the FastAPI server (Assuming your python file is named main.py)
# Start the orchestration script that handles both frontend and backend
CMD ["python", "run.py"]