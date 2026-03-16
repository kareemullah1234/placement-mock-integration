# Run commands (no venv)

You *can* run this project without a virtual environment, but be aware that installing multiple services into the same global Python can cause version conflicts. If you hit weird import/version issues later, switch to per-service venvs (see `LOCAL_SETUP.md`).

## 1) Start Kafka (no Docker)

### Windows (Kafka binaries)

Prereqs:

- Java installed (`java -version` works)
- Apache Kafka downloaded and extracted (example: `C:\kafka_2.13-4.2.0`)

Your error happened because `C:\kafka` doesn't exist on your machine. You already have Kafka extracted at:

- `C:\kafka_2.13-4.2.0`

#### Kafka 4.x (KRaft mode, no ZooKeeper) - recommended

Kafka 4.x does **not** ship `zookeeper-server-start.bat`, so start it in **KRaft** mode.
This repo includes a ready config at `mock_interview_latest/kafka_local/kraft-server.properties`.

From the repo root (`Mock_interview_1-github/mock_interview-main`):

```powershell
$env:KAFKA_HOME="C:\kafka_2.13-4.2.0"   # change if needed

# One-time storage format (copy the UUID it prints)
& "$env:KAFKA_HOME\bin\windows\kafka-storage.bat" random-uuid
& "$env:KAFKA_HOME\bin\windows\kafka-storage.bat" format -t <PASTE_UUID_HERE> -c ".\mock_interview_latest\kafka_local\kraft-server.properties"

# Start Kafka (leave this running)
& "$env:KAFKA_HOME\bin\windows\kafka-server-start.bat" ".\mock_interview_latest\kafka_local\kraft-server.properties"
```

Create topics (run once, new terminal):

```powershell
& "$env:KAFKA_HOME\bin\windows\kafka-topics.bat" --bootstrap-server 127.0.0.1:9092 --create --if-not-exists --topic interview-frames --partitions 1 --replication-factor 1
& "$env:KAFKA_HOME\bin\windows\kafka-topics.bat" --bootstrap-server 127.0.0.1:9092 --create --if-not-exists --topic interview-videos --partitions 1 --replication-factor 1
& "$env:KAFKA_HOME\bin\windows\kafka-topics.bat" --bootstrap-server 127.0.0.1:9092 --list
```

#### Kafka 3.x (ZooKeeper) - only if your Kafka includes ZooKeeper scripts

Open **two** terminals in your Kafka folder (replace `C:\kafka` with your actual folder):

Terminal A (ZooKeeper):

```powershell
cd C:\kafka
.\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties
```

Terminal B (Kafka broker):

1) Edit `C:\kafka\config\server.properties` and set:

```
advertised.listeners=PLAINTEXT://127.0.0.1:9092
```

2) Start Kafka:

```powershell
cd C:\kafka
.\bin\windows\kafka-server-start.bat .\config\server.properties
```

Create topics (run once):

```powershell
cd C:\kafka
.\bin\windows\kafka-topics.bat --bootstrap-server 127.0.0.1:9092 --create --if-not-exists --topic interview-frames --partitions 1 --replication-factor 1
.\bin\windows\kafka-topics.bat --bootstrap-server 127.0.0.1:9092 --create --if-not-exists --topic interview-videos --partitions 1 --replication-factor 1
.\bin\windows\kafka-topics.bat --bootstrap-server 127.0.0.1:9092 --list
```

### Quick troubleshooting (Windows)

```powershell
Test-NetConnection 127.0.0.1 -Port 9092
```

## 1b) Start Kafka (Docker, optional)

This repo also includes a Kafka compose file at `mock_interview_latest/kafka_compose_files/docker-compose-kafka.yaml`.

```powershell
cd mock_interview_latest/kafka_compose_files
docker compose -f docker-compose-kafka.yaml up -d
```

Optional (topics are auto-created, but this makes it explicit):

```powershell
docker exec kafka-frames kafka-topics --bootstrap-server localhost:29092 --create --if-not-exists --topic interview-frames --partitions 1 --replication-factor 1
docker exec kafka-frames kafka-topics --bootstrap-server localhost:29092 --create --if-not-exists --topic interview-videos --partitions 1 --replication-factor 1
```

## 2) Configure Django env

```powershell
cd mock_interview_latest/app
copy .env.example .env
```

If Django is running on your host machine:

- Set `KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092`

If Django is running inside Docker on the same network as Kafka:

- Set `KAFKA_BOOTSTRAP_SERVERS=kafka-frames:29092`

## 3) Run Django (without venv)

```powershell
cd mock_interview_latest/app
python -m pip install --user -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## 4) Quick Kafka check (from Django app folder)

```powershell
cd mock_interview_latest/app
python quick_kafka_test.py
```

## 5) Kafka diagnostic endpoint (staff only)

After the server starts:

- `http://localhost:8000/interview/api/diagnostic/kafka/`

If Kafka is reachable, it should show `connected: true` and topic info.
