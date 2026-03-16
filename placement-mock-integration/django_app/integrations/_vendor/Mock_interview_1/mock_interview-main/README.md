# 🎤 Mock Interview Platform

An AI-powered automated mock interview system designed to conduct technical interviews for students without human interviewers. The platform leverages cutting-edge AI technologies including real-time Speech-to-Text, dynamic question generation, and comprehensive behavioral analysis.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Folder Structure](#folder-structure)
- [Features](#features)
- [Interview Flow](#interview-flow)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)

---

## 🎯 Overview

The Mock Interview Platform automates the entire interview process:

1. **Students** register, set availability, and request interviews
2. **Admins** approve/reject requests and schedule interviews
3. **AI Interviewer** conducts 15-question interviews across 6 stages
4. **Real-time Analysis** captures video frames and audio responses
5. **Background Processing** analyzes behavior and generates reports
6. **Automated Emails** deliver comprehensive feedback to students

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MOCK INTERVIEW PLATFORM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Student   │    │    Admin    │    │   Django    │    │   Airflow   │  │
│  │   Browser   │───▶│  Dashboard  │───▶│  Container  │───▶│    DAGs     │  │
│  └─────────────┘    └─────────────┘    └──────┬──────┘    └─────────────┘  │
│                                               │                             │
│         ┌─────────────────────────────────────┼─────────────────────────┐   │
│         │                                     │                         │   │
│         ▼                                     ▼                         ▼   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │    Kafka    │    │    HDFS     │    │   MySQL 8   │    │    Dlib     │  │
│  │   Broker    │    │   Cluster   │    │  Database   │    │  Container  │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Docker Containers

| Container | Port | Purpose |
|-----------|------|---------|
| Django Web App | 8000 | Main application, APIs, templates |
| MySQL 8.0 | 3306 | Primary database |
| HDFS Namenode | 9870 | Audio file storage |
| Kafka Broker | 9092 | Video frame/chunk streaming |
| Zookeeper | 2181 | Kafka coordination |
| Kafka UI | 8081 | Monitoring dashboard |
| Dlib Container | 5001 | Behavioral video analysis |
| Audio API | 5000 | Transcription & grading |
| Airflow | 8080 | DAG scheduler |

---

## 🛠 Technology Stack

### Backend
- **Framework:** Django 4.2.7
- **Database:** MySQL 8.0
- **Task Queue:** Apache Airflow
- **Message Broker:** Apache Kafka
- **Storage:** HDFS (Hadoop Distributed File System)

### AI/ML Services
- **Speech-to-Text:** Google Gemini (gemini-1.5-flash)
- **Question Generation:** LLaMA 3.2 via OpenRouter
- **Text-to-Speech:** gTTS (Google Text-to-Speech)
- **Response Grading:** DeepSeek via OpenRouter
- **Video Analysis:** Dlib + MediaPipe + OpenCV

### Audio Analysis
- **Libraries:** Librosa, OpenSMILE, Parselmouth (Praat)
- **Metrics:** Pitch, jitter, shimmer, speech rate, pauses

---

## 📁 Folder Structure

```
mock_interview/
├── dag_scripts/                          # Airflow DAG definitions
│   ├── consolidated_interview_processor_llm.py  # Main processing DAG
│   └── interview_status_email_notifications.py  # Email notification DAG
│
├── dlib_video/                           # Dlib Container Code
│   ├── combined_interview_analyzer.py    # Video behavioral analysis
│   ├── requirements.txt                  # Python dependencies
│   └── interview_results/                # Generated analysis JSONs
│
├── mock_interview_audio_api/             # Audio API Container
│   └── app/
│       ├── app.py                        # Flask API for transcription
│       ├── Dockerfile                    # Container build
│       └── requirements.txt              # Dependencies
│
├── mock_interview_latest/                # Django Web Application
│   ├── kafka_compose_files/
│   │   └── docker-compose-kafka.yaml     # Kafka stack compose
│   │
│   └── app/
│       ├── manage.py                     # Django management
│       ├── requirements.txt              # Python dependencies
│       ├── Dockerfile                    # Container build
│       │
│       ├── interview_system/             # Core interview app
│       │   ├── models.py                 # Interview, InterviewFrames, etc.
│       │   ├── views.py                  # 3000+ lines - all APIs
│       │   └── urls.py                   # URL routing
│       │
│       ├── user_management/              # User & auth app
│       │   ├── models.py                 # CustomUser, StudentProfile
│       │   └── views.py                  # Login, register, dashboards
│       │
│       ├── utils/                        # Utility modules
│       │   ├── hdfs_client.py            # HDFS file operations
│       │   └── kafka_client.py           # Kafka producer/consumer
│       │
│       ├── templates/                    # HTML templates
│       │   ├── user_management/
│       │   │   ├── admin_dashboard.html
│       │   │   ├── student_dashboard.html
│       │   │   └── login.html
│       │   └── interview_system/
│       │       └── interview.html        # Main interview interface
│       │
│       └── _archived/                    # Deprecated code (reference only)
│
├── generate_documentation.py             # Documentation generator
├── .gitignore                            # Git ignore rules
└── README.md                             # This file
```

---

## ✨ Features

### For Students
- 📝 Register with college and course details
- 📅 Set 3 availability time slots
- 🎤 Take AI-powered voice interviews
- 📊 Receive detailed feedback reports via email
- 📈 Track interview history and scores

### For Admins
- 👥 View and manage all interview requests
- ✅ Approve/reject with scheduled times
- 📺 Watch student interview recordings
- 📋 Monitor interview progress in real-time
- 📧 Automated email notifications

### AI Interview System
- 🤖 15 questions across 6 topic stages
- 🎯 Context-aware follow-up questions
- 🔊 Natural voice interaction (TTS/STT)
- 👁 Real-time behavioral analysis
- 📹 Video recording and playback

---

## 🎤 Interview Flow

### Question Stages (15 Questions Total)

| Stage | Questions | Focus Areas |
|-------|-----------|-------------|
| **1. Introduction** | Q1-Q3 | Background, career goals, motivation |
| **2. Projects** | Q4-Q6 | Past work, challenges, outcomes |
| **3. Python** | Q7-Q9 | Data structures, OOP, libraries |
| **4. Statistics** | Q10-Q12 | Probability, distributions, testing |
| **5. Machine Learning** | Q13-Q14 | Algorithms, evaluation, applications |
| **6. Closing** | Q15 | Final questions, wrap-up |

### Data Flow During Interview

```
Student speaks → Browser records audio → Gemini STT transcribes
     ↓
LLaMA generates next question → gTTS converts to speech → Plays in browser
     ↓
Audio saved to HDFS → Frames streamed to Kafka → Video chunks saved
     ↓
Interview ends → DAG triggered → Dlib analyzes behavior
     ↓
Report generated → Email sent to student
```

---

## 🚀 Setup & Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- MySQL 8.0
- Hadoop/HDFS cluster

### 1. Clone Repository
```bash
git clone <repository-url>
cd mock_interview
```

### 2. Create Docker Network
```bash
docker network create docker-hadoop_default
```

### 3. Start Kafka Stack
```bash
cd mock_interview_latest/kafka_compose_files
docker-compose -f docker-compose-kafka.yaml up -d
```

### 4. Create Kafka Topics
```bash
docker exec kafka-frames kafka-topics --bootstrap-server localhost:9092 --create --topic interview-frames --partitions 1 --replication-factor 1
docker exec kafka-frames kafka-topics --bootstrap-server localhost:9092 --create --topic interview-videos --partitions 1 --replication-factor 1
```

### 5. Start Django Application
```bash
cd mock_interview_latest/app
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### 6. Configure Airflow DAGs
Copy DAG files to your Airflow DAGs folder:
```bash
cp dag_scripts/*.py /path/to/airflow/dags/
```

---

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True

# Database
DB_NAME=mock_interview_platform
DB_USER=root
DB_PASSWORD=your-password
DB_HOST=mysql8-container
DB_PORT=3306

# HDFS
HDFS_HOST=192.168.1.123
HDFS_PORT=9870
HDFS_USER=hdfs

# AI APIs
OPENROUTER_API_KEY=sk-or-v1-xxxxx
GEMINI_API_KEY=AIzaSyxxxxx
```

### Kafka Configuration
- **Broker:** kafka-frames:9092
- **Topics:** interview-frames, interview-videos
- **Retention:** Infinite (-1)

---

## 📡 API Documentation

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/interview/start/<id>/` | Start an approved interview |
| POST | `/interview/api/voice-interview/start/` | Begin voice interview session |
| POST | `/interview/api/voice-interview/process/` | Process voice response |
| POST | `/interview/api/save-audio-response/` | Save audio to HDFS |
| POST | `/interview/api/stream-frame/` | Stream video frame to Kafka |
| POST | `/interview/api/stream-video-chunk/` | Stream video chunk to Kafka |
| GET | `/interview/api/kafka-video/<id>/` | Retrieve reconstructed video |
| POST | `/interview/api/end-interview/` | End interview session |

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/interview/api/interviews/` | List all interviews |
| POST | `/interview/api/approve/<id>/` | Approve interview request |
| POST | `/interview/api/reject/<id>/` | Reject interview request |
| GET | `/interview/api/video-info/<id>/` | Get video availability info |

---

## 📊 Database Models

### Core Models
- **CustomUser** - Extended Django user with candidate_id
- **StudentProfile** - Student details and availability
- **Interview** - Main interview tracking (25+ fields)
- **InterviewResponse** - Individual Q&A with HDFS paths
- **InterviewFrames** - Kafka session tracking
- **VoiceInterviewSession** - Voice interview state

---

## 🔄 Background Processing

### DAGs (Apache Airflow)

1. **consolidated_interview_processor_llm**
   - Schedule: Every 40 minutes
   - Processes completed interviews
   - Triggers Dlib behavioral analysis
   - Generates PDF reports
   - Sends email notifications

2. **interview_status_email_notifications**
   - Sends approval/rejection emails
   - Tracks email delivery status

---

## 🔒 Repository Access

This is a **private repository** with restricted access. Only authorized team members can view, clone, or contribute to this codebase.

### For Internal Team Members
1. Ensure you have repository access granted by the admin
2. Clone using SSH: `git clone git@github.com:rubixe/mock-interview.git`
3. Create feature branches for new development
4. Submit pull requests for code review before merging

### Branch Strategy
- `main` - Production-ready code
- `develop` - Development integration branch
- `feature/*` - New features
- `hotfix/*` - Production bug fixes

---

## 📄 License

**⚠️ CONFIDENTIAL - Internal Use Only**

This project is proprietary software developed by **Rubixe** for educational mock interview purposes.

**© 2026 Rubixe. All Rights Reserved.**

This software and its documentation are confidential and proprietary. Unauthorized copying, distribution, modification, or use of this software, via any medium, is strictly prohibited without prior written permission from Rubixe.


---

## 📞 Support & Contact

### Technical Support
For technical issues, bugs, or feature requests:
- 🐛 **Issue Tracker:** Create an issue in the repository
- 📚 **Documentation:** Refer to `Mock_Interview_Platform_Documentation.docx`

### Development Team
- **Project Lead:** Rubixe Development Team

### Response Times
| Priority | Response Time |
|----------|---------------|
| Critical (Production Down) | 4 hours |
| High (Major Feature Broken) | 24 hours |
| Medium (Minor Issues) | 48 hours |
| Low (Enhancements) | 1 week |

---

## 🙏 Acknowledgments

- **Google Gemini** - Speech-to-Text capabilities
- **Meta LLaMA** - AI question generation via OpenRouter
- **Apache Kafka** - Real-time streaming infrastructure
- **Apache Airflow** - Workflow orchestration
- **Dlib & MediaPipe** - Facial analysis and computer vision

---

