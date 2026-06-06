from setuptools import setup, find_packages

setup(
    name="obby",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "rich",
        "questionary",
        "prompt_toolkit",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "obby=obby_core.app:main",
        ],
    },
    author="magentaong",
    description="A local-first Obsidian planning assistant",
    python_requires=">=3.8",
)
