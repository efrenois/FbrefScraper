from setuptools import setup, find_packages
from pathlib import Path

HERE = Path(__file__).parent
README = (HERE / "README.md").read_text(encoding="utf-8") if (HERE / "README.md").exists() else ""

setup(
    name="fbref-scrapper",
    version="0.1.0",
    description="Simple FBref scraper for football statistics",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Your Name",
    url="https://github.com/yourusername/FbrefScrapper",
    packages=find_packages(exclude=("tests", "docs")),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "requests",
        "beautifulsoup4",
        "lxml",
        "pandas",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            # change target to your package's CLI entry point if present
            "fbref-scraper=fbrefscrapper.__main__:main",
        ]
    },
)