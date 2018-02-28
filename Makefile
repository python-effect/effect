lint:
	flake8 --ignore=E131,E301,E302,E731,W503,E701,E704,E722 --max-line-length=100 effect/

build-dist:
	rm -rf dist
	python setup.py sdist bdist_wheel

upload-dist:
	twine upload dist/*
	echo
	echo "Don't forget to:"
	echo "- add a git tag."
	echo "- add release notes to GitHub"
	echo "- bump the version in setup.py and docs/source/conf.py."

doc:
	rm -rf docs/build
	rm -rf docs/source/api
	cd docs; sphinx-apidoc -e -o source/api ../effect ../setup.py ../examples ../effect/test_*.py
	rm docs/source/api/modules.rst
	rm docs/source/api/effect.rst
	# can't use sed -i on both linux and mac, so...
	# sed -e 's/Module contents/Core API/' docs/source/api/effect.rst > .effect.rst
	# mv .effect.rst docs/source/api/effect.rst
	# sed -e 's/effect package/API docs/' docs/source/api/effect.rst > .effect.rst
	# mv .effect.rst docs/source/api/effect.rst
	cd docs; PYTHONPATH=..:$(PYTHONPATH) sphinx-build -W -b html -d build/doctrees source build/html
