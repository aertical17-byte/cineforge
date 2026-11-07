.PHONY: help install-api install-web api web worker test-api test-web compose-up compose-down migrate verify-providers clean

help:
	@echo "make install-api | install-web | api | web | worker | test-api | test-web | migrate | verify-providers | compose-up | compose-down"

install-api:
	cd apps/api && python3 -m pip install -r requirements.txt -r requirements-dev.txt

api:
	cd apps/api && uvicorn app.main:app --reload --port 8000

worker:
	cd apps/api && python3 -m app.worker_loop

install-web:
	cd apps/web && npm install

web:
	cd apps/web && npm run dev

test-api:
	cd apps/api && AI_MOCK_MODE=1 python3 -m pytest -q

test-web:
	cd apps/web && npm run test

migrate:
	cd apps/api && alembic upgrade head

verify-providers:
	cd apps/api && python3 scripts/verify_providers.py

compose-up:
	docker compose -f infra/docker/docker-compose.yml up --build

compose-down:
	docker compose -f infra/docker/docker-compose.yml down

clean:
	rm -rf data logs htmlcov .pytest_cache apps/web/.next
