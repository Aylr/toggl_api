from setuptools import setup, find_packages

setup(
    name="toggl",
    version="0.2.0",
    url="https://github.com/Aylr/toggl_api",
    author="Taylor Miller",
    description="Toggl datawrangling in python.",
    packages=find_packages(),
    install_requires=[
        "certifi",
        "pandas",
        "pyaml",
        "dateparser",
    ],
)
