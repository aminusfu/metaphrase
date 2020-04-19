# pragma: no cover
from setuptools import setup, find_packages

setup(
    name='metaphrase',
    version='0.1.0',
    author="Robert Brewer",
    author_email="fumanchu@aminus.org",
    packages=find_packages('.'),
    package_dir={'metaphrase': 'metaphrase'},
    install_requires=[
        'simplejson>=2.6.2',
        'CherryPy==3.2.4',
        'py-bcrypt>=0.4.0',
    ],
    entry_points={
        #'console_scripts': ['metaphrase = metaphrase.run:main']
    }
)
