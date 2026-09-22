#!/bin/bash

cd /home/ubuntu/InternTrack-Cloud

source .venv/bin/activate

export FLASK_ENV=production
export FLASK_DEBUG=False

gunicorn --bind 0.0.0.0:5000 app:app