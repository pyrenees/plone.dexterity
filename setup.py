# -*- coding: utf-8 -*-
import sys
from setuptools import setup
from setuptools import find_packages


version = '2.4.2.dev0'

short_description = """\
Framework for content types as filesystem code and TTW (Zope/CMF/Plone)\
"""
long_description = open("README.rst").read() + "\n"
long_description += open("CHANGES.rst").read()

setup(
    name='plone.dexterity',
    version=version,
    description=short_description,
    long_description=long_description,
    # Get more strings from
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Framework :: Plone",
        "Framework :: Plone :: 5.0",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords='plone dexterity contenttypes',
    author='Martin Aspeli',
    author_email='optilude@gmail.com',
    url='https://pypi.python.org/pypi/plone.dexterity',
    license='GPL version 2',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['plone'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',
        'python-dateutil',
        'plone.behavior>=1.0b5',
        'plone.supermodel>=1.0b2',
        'plone.synchronize',
        'plone.uuid',
        'zope.annotation',
        'zope.browser',
        'zope.component',
        'zope.container',
        'zope.dottedname',
        'zope.interface',
        'zope.lifecycleevent',
        'zope.location',
        'zope.publisher',
        'zope.schema',
        'zope.security',
        'zope.securitypolicy',
        'zope.size',
        'zope.dublincore',
        'ZODB',
    ],
    extras_require={
        'test': [
            'plone.mocktestcase>=1.0b3',
            'plone.testing',
            'mock',
        ]
    },
    entry_points="""
    # -*- Entry points: -*-
    """,
)
