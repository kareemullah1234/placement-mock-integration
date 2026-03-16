# PlacementPortal

Single integrated Django app lives in `PlacementPortal/` (see `PlacementPortal/integrations/` for services/pipelines/DAGs).

## Quickstart (SQLite default)

```powershell
pip install -r requirements.txt
python PlacementPortal\manage.py migrate
python PlacementPortal\manage.py runserver
```

## MySQL (optional)

Set `DB_ENGINE=mysql` plus `DB_*` variables (see `PlacementPortal/.env.example`).
