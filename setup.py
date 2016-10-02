# encoding = utf-8
from __future__ import print_function

import os
import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

import vxTrader

here = os.path.abspath(os.path.dirname(__file__))

requirements = [
    'six',
    'requests',
    'numpy',
    'pandas',
    'pytesseract',
    'demjson',
    'Pillow'
]

readme = None
long_description = ''
if os.path.exists('README.md'):
    readme = 'README.md'
elif os.path.exists('README.rst'):
    readme = 'README.rst'

if readme:
    with open(readme, 'rb') as f:
        long_description = f.read().decode('utf-8')




class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errcode = pytest.main(self.test_args)
        sys.exit(errcode)


setup(
    name='vxTrader',
    version=vxTrader.__version__,
    url='https://github.com/vex1023/vxTrader/',
    license='The MIT License (MIT)',
    author='vex1023',
    author_email='vex1023@qq.com',
    tests_requires=['pytest'],
    install_requires=requirements,
    cmdclass={'test': PyTest},
    description='vxTrader: A Chinese WebAPI wrapper',
    long_description=long_description,
    packages=find_packages(),
    include_package_data=True,
    platforms='any',
    test_suite='vxTrader.tests.test_vxTrader',
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: Chinese',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ),
    extras_require={
        'testing': ['pytest']
    }
)
