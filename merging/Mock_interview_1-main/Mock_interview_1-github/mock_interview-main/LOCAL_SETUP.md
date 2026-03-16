# Local setup / fixing common errors

This repo contains multiple Python services. Each service has its own dependencies and (ideally) its own virtual environment.

## Services

- Django web app: `mock_interview_latest/app` (run `manage.py`)
- Audio analysis API (Flask): `mock_interview_audio_api/app` (run `app.py`)
- Video analysis: `dlib_video` (run `combined_interview_analyzer.py`)
- Airflow DAGs: `dag_scripts` (runs inside an Airflow environment)

## Recommended: one virtualenv per service (Windows / PowerShell)

### Django app

```powershell
cd mock_interview_latest/app
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
python manage.py check
python manage.py runserver
```

### Audio API

```powershell
cd mock_interview_audio_api/app
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
python app.py
```

### Video analysis

```powershell
cd dlib_video
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
python combined_interview_analyzer.py --help
```

Note: `dlib` can be difficult to install on Windows (build tools are often required). Running `dlib_video` inside Docker/WSL is usually easier.

## Common errors and what they mean

- `ModuleNotFoundError: No module named 'speech_recognition'`
  - Install the service dependencies (`pip install -r requirements.txt`) from the folder you are running (`mock_interview_audio_api/app` or `mock_interview_latest/app`).
- `ModuleNotFoundError: No module named 'cv2'`
  - Install OpenCV (`opencv-python`) via `dlib_video/requirements.txt`.
- Errors importing `dag_scripts/*` like missing `airflow` or `fpdf`
  - Expected unless you are running inside an Airflow environment. Install Airflow and `fpdf2` in the Airflow image/venv.

## Environment variables

- Django reads `mock_interview_latest/app/.env` (see `mock_interview_latest/app/.env.example`).
- Audio API can also read env vars (see `mock_interview_audio_api/app/.env.example`).
