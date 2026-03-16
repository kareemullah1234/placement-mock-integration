# PlacementPortal (Django)

## Run (SQLite default)

```powershell
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Configuration

- Copy `./.env.example` to `./.env` and set values as needed.
- MySQL: set `DB_ENGINE=mysql` and `DB_*` vars.

## Included Components

- `./integrations/services/` contains supporting APIs (ex: `mock_interview_audio_api`).
- `./integrations/pipelines/` contains offline processing scripts (ex: `dlib_video`).
- `./integrations/airflow/` contains Airflow DAGs for background processing.
