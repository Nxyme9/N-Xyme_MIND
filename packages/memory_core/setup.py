from setuptools import setup

setup(
    name="n-xyme-memory-core",
    version="0.1.0",
    packages=["memory_core"],
    package_dir={"memory_core": "."},
    package_data={"memory_core": ["*.md", "*.json"]},
    install_requires=[
        "chromadb>=0.4.0",
        "networkx>=3.0",
        "numpy>=1.24.0",
    ],
)
