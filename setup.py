#!/usr/bin/env python
"""The setup script."""

from setuptools import setup, find_packages

def read_requirements(path: str):
    with open(path) as f:
        return f.read().splitlines()

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.md') as history_file:
    history = history_file.read()

install_requirements = read_requirements("requirements.txt")

setup(
    author="Brandon Rose",
    author_email='brandon@jataware.com',
    python_requires='>=3.5',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="The Domain Modeler Workbench",
    install_requires=install_requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='dojo',
    name='dojo',
    packages=find_packages(include=['dojo', 'dojo.*']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/brandomr/dojo',
    version='0.1.0',
    zip_safe=False,
)
