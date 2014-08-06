lint:
	flake8 --ignore=E131 effect/ examples/

build-dist:
	rm -rf dist
	python setup.py sdist bdist_wheel

upload-dist:
	twine upload dist/*
