#!/bin/bash
# Start Backend API

init() {
    cd /app

    # Activate our virtual environment here
    . /opt/pysetup/.venv/bin/activate
}

init
exec python marvin/app.py
