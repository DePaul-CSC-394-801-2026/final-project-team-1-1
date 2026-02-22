#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

pushd app >/dev/null
python3 manage.py collectstatic --no-input
python3 manage.py migrate
popd >/dev/null
