from setuptools import setup, find_packages

setup(
    name="nba_downloader",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.2",
        "selenium>=4.15.2",
        "tqdm>=4.66.1",
        "you-get>=0.4.1650",
        "webdriver-manager>=4.0.1",
    ],
    entry_points={
        'console_scripts': [
            'nba-downloader=nba_downloader.nba_video_downloader:main',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool to download NBA game videos",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/nba-downloader",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
