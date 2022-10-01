#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

VENVPATH="./venv"

venv() {
    echo "source ${VENVPATH}/bin/activate"
}

make-venv() {
    mkdir -p "${HOME}/.venv"
    python -m venv "${VENVPATH}"
}

reset-venv() {
    rm -rf "${VENVPATH}"
    make-venv
}

wrapped-python() {
    "${VENVPATH}"/bin/python "$@"
}

wrapped-pip() {
    wrapped-python -m pip "$@"
}

python-deps() {
    wrapped-pip install --upgrade pip setuptools wheel

    local pip_extras="${1:-}"
    if [ -z "${pip_extras}" ]; then
        wrapped-pip install -e .
    else
        wrapped-pip install -e ".[${pip_extras}]"
    fi
}

install() {
    if [ -d "${VENVPATH}" ]; then
        python-deps "$@"
    else
        make-venv && python-deps "$@"
    fi
}

build() {
    python -m build
}

publish() {
    clean && build
    python -m twine upload dist/*
}

clean() {
    rm -rf dist/
    rm -rf .eggs/
    rm -rf build/
    find . -name '*.pyc' -exec rm -f {} +
    find . -name '*.pyo' -exec rm -f {} +
    find . -name '*~' -exec rm -f {} +
    find . -name '__pycache__' -exec rm -fr {} +
    find . -name '.mypy_cache' -exec rm -fr {} +
    find . -name '.pytest_cache' -exec rm -fr {} +
    find . -name '*.egg-info' -exec rm -fr {} +
}

lint() {
    wrapped-python -m flake8 src/
    wrapped-python -m mypy src/
}

tests() {
    wrapped-python -m pytest -rP tests/
}

get-htmx() {
    htmx_version="1.8.0"
    htmx_extensions=("json-enc" "sse")

    mkdir -p htmx/ext
    wget -P htmx/ "https://unpkg.com/htmx.org@${htmx_version}/dist/htmx.js"
    wget -P htmx/ "https://unpkg.com/htmx.org@${htmx_version}/dist/htmx.min.js"

    for ext in "${htmx_extensions[@]}"; do
        wget -P htmx/ext/ "https://unpkg.com/htmx.org@${htmx_version}/dist/ext/${ext}.js"
    done;
}

default() {
    QUART_APP=quart_sse_demo.server:app \
        wrapped-python -m quart --debug run --host 0.0.0.0 --port 8081 --reload
}

TIMEFORMAT="Task completed in %3lR"
time "${@:-default}"
