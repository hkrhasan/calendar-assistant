IMAGE ?= calendar-assistant


.PHONY: build
build:
	docker build -t ${IMAGE} .

.PHONY: start
start:
	docker run -p 8000:8000 -p 8501:8501 --env-file .env calendar-assistant