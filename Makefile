BACKEND_IMAGE ?= calendar-assistant-backend
FRONTEND_IMAGE ?= calendar-assistant-frontend 

.PHONY: build-backend
build-backend:
	docker build -f ./Dockerfile.backend -t ${BACKEND_IMAGE} .

.PHONY: start-backend
start-backend:
	docker run -p 8000:8000 --env-file .env ${BACKEND_IMAGE} 

.PHONY: build-frontend
build-frontend:
	docker build -f ./Dockerfile.frontend -t ${FRONTEND_IMAGE} .

.PHONY: start-frontend
start-frontend:
	docker run -p 8000:8000 --env-file .env ${FRONTEND_IMAGE}


.PHONY: get-b64-cred
get-b64-cred:
	base64 credentials.json | tr -d '\n'
