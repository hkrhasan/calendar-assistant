#!/bin/bash

# Start backend
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 