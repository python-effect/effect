#!/usr/bin/env python
import setuptools

setuptools.setup(
    name="effect",
    version="0.1a6",
    description="pure effects for Python",
    long_description=open('README.rst').read(),
    url="http://github.com/radix/effect/",
    author="Christopher Armstrong",
    license="MIT",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        ],
    packages=['effect'],
    install_requires=['six'],
    )
