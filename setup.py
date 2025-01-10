from setuptools import setup, find_packages

setup(
    name="demo",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "python-dotenv>=1.0.0",
        "langchain>=0.3,<0.4",
        "langchain-community>=0.3.0",
        "langchain-core>=0.1.0",
        "google-search-results>=2.4.2",
    ]
) 