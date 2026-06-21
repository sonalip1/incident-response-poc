1. python test_env.py
2. python tests/test_orchestrator.py
3. python scripts/seed_db.py
   python tests/test_orchestrator.py
4. python tests/test_degradation.py
5. python tests/test_orchestrator.py
6. python main.py --seed


========
Test backend apis:
source venv/bin/activate
uvicorn backend.main:app --reload
curl -X POST -H "Content-Type: application/json" -d '{"log_text": "2025-05-10 02:14:33 ERROR payment-service    DB connection timeout after 30000ms\n2025-05-10 02:14:40 ERROR payment-service    Unhandled exception: PSQLException: too many connections"}' http://127.0.0.1:8000/api/incidents
curl -N http://127.0.0.1:8000/api/incidents/3960e1c9-3c3e-435c-87e5-75367d96c635/stream
curl -X POST -H "Content-Type: application/json" -d '{"approved": true}' http://127.0.0.1:8000/api/incidents/3960e1c9-3c3e-435c-87e5-75367d96c635/approve

========







