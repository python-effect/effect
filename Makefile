lint:
	flake8 --ignore=E131 effect/ examples/

build-dist:
	rm -rf dist
	python setup.py sdist bdist_wheel

upload-dist:
	twine upload dist/*
	echo
	echo "Don't forget to add a git tag."

doc:
	rm -rf docs/build
	rm -rf docs/source/api
	cd docs; sphinx-apidoc -e -o source/api ../effect ../setup.py ../examples ../effect/test_*.py
	cd docs; PYTHONPATH=..:$(PYTHONPATH) sphinx-build -W -b html -d build/doctrees source build/html
