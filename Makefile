.PHONY: test backend-test frontend-test build integration health e2e down

test: backend-test frontend-test

backend-test:
	docker build --target test -t ohohops-backend-test backend
	docker run --rm -e DEPLOYMENT_MODE=local -e CHROMA_HOST=chromadb -v "$(CURDIR):/workspace" -w /workspace/backend ohohops-backend-test python -m pytest --cov=app --cov-report=term-missing

frontend-test:
	cd frontend && npm ci
	cd frontend && npm run lint
	cd frontend && npm run build

build:
	docker compose build

integration:
	docker compose -f docker-compose.yml -f docker-compose.test.yml up -d --build

health:
	curl --fail http://127.0.0.1:8000/api/v1/health

e2e:
	cd frontend && npm run test:e2e

down:
	docker compose down
