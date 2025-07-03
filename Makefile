IMAGE ?= calendar-assistant-backend


.PHONY: build-backend
build-backend:
	docker build -f ./Dockerfile.backend -t ${IMAGE} .

.PHONY: start-backend
start-backend:
	docker run -p 8000:8000 --env-file .env ${IMAGE} 