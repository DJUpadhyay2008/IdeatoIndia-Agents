from setuptools import setup, find_packages

setup(
    name="ideatoindia-common",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "pypdf"
    ],
    description="Shared utility library for IdeaToIndia strategy agents",
)
