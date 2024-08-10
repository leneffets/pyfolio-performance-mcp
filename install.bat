rm -rf dist
python setup.py sdist bdist_wheel
twine check dist/*
pip install --force-reinstall dist/pyfolio_performance-0.2.4-py3-none-any.whl