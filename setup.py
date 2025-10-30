"""Setup file for ROA Agent"""
from setuptools import setup, find_packages

setup(
    name="roa-agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langgraph",
        "langchain-google-genai",
        "langchain-core",
        "neo4j",
        "python-dotenv",
    ],
)
