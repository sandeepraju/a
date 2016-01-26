from setuptools import setup

setup(
    name='cmanager',
    version='0.1',
    url='https://github.com/sandeepraju/a/line-of-credit',
    author='Sandeep Raju Prabhakar',
    author_email='SandeepPrabhakar2015@u.northwestern.edu',
    packages=['cmanager'],
    description='A simple library to manage a credit.',
    long_description=open('README.md').read(),
    install_requires=[
        'psycopg2==2.6.1',
    ],
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ]
)

