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
	cd docs; sphinx-apidoc -o source/api ../effect ../setup.py ../examples
	cd docs; PYTHONPATH=..:$(PYTHONPATH) sphinx-build -nW -b html -d build/doctrees source build/html
