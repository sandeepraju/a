
.PHONY: all clean build install uninstall test

all: clean

clean:
	find . -name \*.pyc -delete
	find . -name \*.pyo -delete
	find . -name \*~ -delete
	rm -rf dist cmanager.egg-info

build:
	python setup.py sdist

install:
	pip install dist/cmanager-*.tar.gz

uninstall:
	yes | pip uninstall cmanager

test:
	python -m tests.cmanager_tests
