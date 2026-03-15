#!/bin/bash
nohup python ./app/main.py > ./web.log 2>&1 &
celery -A app.tasks.backend worker -l info