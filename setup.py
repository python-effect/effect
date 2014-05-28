#!/usr/bin/env python
import setuptools

setuptools.setup(
    name="effect",
    version="0.1a1",
    description="pure effects for Python",
    long_description="A way to isolate effects (IO and state manipulation) "
                     "from the rest of your code",
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
    )
