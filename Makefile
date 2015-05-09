lint:
	flake8 --ignore=E131,E731,W503 effect/

build-dist:
	rm -rf dist
	python setup.py sdist bdist_wheel

upload-dist:
	twine upload dist/*
	echo
	echo "Don't forget to add a git tag."
	echo "And don't forget to bump the version in setup.py and docs/source/conf.py."

doc:
	rm -rf docs/build
	rm -rf docs/source/api
	cd docs; sphinx-apidoc -e -o source/api ../effect ../setup.py ../examples ../effect/test_*.py
	cd docs; PYTHONPATH=..:$(PYTHONPATH) sphinx-build -W -b html -d build/doctrees source build/html
