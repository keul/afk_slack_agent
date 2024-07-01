#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = ["Click>=7.0", "pyobjc-framework-notificationcenter", "slack_sdk", "psutil"]

test_requirements = [
    "pytest>=3",
]

setup(
    author="Luca Fabbri",
    author_email="lucafbb@gmail.com",
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: MacOS X",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
    description="Signal your A.F.K. status on Slack automatically",
    entry_points={
        "console_scripts": [
            "afk_agent=afk_slack_agent.agent:main",
            "afk=afk_slack_agent.client:main",
        ],
    },
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme,
    include_package_data=True,
    keywords="afk_slack_agent",
    name="afk_slack_agent",
    packages=find_packages(include=["afk_slack_agent", "afk_slack_agent.*"]),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/keul/afk_slack_agent",
    version="0.2.1.dev0",
    zip_safe=False,
)
