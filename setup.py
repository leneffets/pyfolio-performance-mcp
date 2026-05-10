# Always prefer setuptools over distutils
from setuptools import setup, find_packages

# To use a consistent encoding
from codecs import open
from os import path

# The directory containing this file
HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# This call to setup() does all the work
setup(
    name="pyfolio-performance",
    version="0.3.0",
    description="Python library + MCP server for Portfolio Performance XML files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/leneffets/pyfolio-performance-mcp",
    project_urls={
        "Bug Tracker": "https://github.com/leneffets/pyfolio-performance-mcp/issues",
    },
    author="Fabian Bendun",
    author_email="pyfolio-performance@bendun.io",
    license="MIT",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Financial",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="portfolio-performance mcp investment finance trading etf stocks",
    packages=["pyfolio_performance"],
    include_package_data=True,
    install_requires=["xmltodict"]
)