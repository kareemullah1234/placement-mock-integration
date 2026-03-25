# AI Mock Interview System

## Overview
A comprehensive technical interview platform featuring AI-powered voice based interactions, real-time video/frame streaming, behavioral tracking through proctoring, and Gemini-driven performance analysis.

## Core Features
- **Voice Interview Flow**: 15 technical questions asked by a synthetic AI interviewer (using Google Gemini 1.5 Flash).
- **Dual Input Processing**: Supports both high-quality audio streaming and real-time text fallbacks for maximum reliability.
- **Proctoring System**: Tracks violations (tab switching, screen sharing status) with a 10-second grace period.
- **Microservice Architecture**:
  - **Django**: Core business logic and candidate/company dashboards.
  - **Docker**: Containerized deployment for consistent environment setup.
  - **Kafka**: Real-time video frame and audio chunk streaming.
  - **HDFS**: Distributed storage for long-term video and audio persistence.

## Current Setup & Configuration
- **Gemini AI API**: Core brain for STT (Speech-to-Text) and Question generation.
- **OpenRouter (DeepSeek R1)**: Powers the final interview analysis report.
- **Kafka Service Name**: `kafka:9092` (Internal Docker network).
- **Database**: 185 technical and general questions seeded in the `Question` model.

## Installation & Startup (from WSL)
1. **Navigate to project directory**:
   ```bash
   cd "OneDrive/Desktop/originial/integrated_app"
   ```
2. **Start the containers**:
   ```bash
   docker compose up -d --build
   ```
3. **Database Setup inside Docker**:
   ```bash
   # First, create the migration file for the new changes
   docker compose exec web python manage.py makemigrations interviews

   # Then, apply that file to the database
   docker compose exec web python manage.py migrate

   # Seed the interview questions
   docker compose exec web python manage.py seed_questions
   ```
4. **Environment Variables**:
   Update your `.env` file with real API keys:
   - `GEMINI_API_KEY`: Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
   - `OPENROUTER_API_KEY`: Get from [OpenRouter](https://openrouter.ai/) for DeepSeek R1 reports.

## Troubleshooting
- **"Processing failed"**: Usually caused by an invalid or expired `GEMINI_API_KEY` or missing database columns (run `makemigrations`).
- **Kafka NoBrokersAvailable**: Ensure Kafka/Zookeeper are healthy using `docker compose ps` and `docker compose restart kafka`.
- **Audio/Video errors**: Best tested in Chrome; ensure microphone and camera permissions are granted.
