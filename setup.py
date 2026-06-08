from setuptools import setup, find_packages

setup(
    name="datacollector",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0",
        "pandas>=2.0",
        "openpyxl>=3.1",
        "Pillow>=10.0",
    ],
    entry_points={
        "console_scripts": [
            "dc=datacollector.cli:cli",
        ],
    },
)
