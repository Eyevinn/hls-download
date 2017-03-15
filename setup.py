from os.path import dirname, abspath, join, exists
from setuptools import setup

try:
    from pypandoc import convert
    read_md = lambda f: convert(f, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")
    read_md = lambda f: open(f, 'r').read()

long_description = None
if exists("README.md"):
    long_description = read_md("README.md")

install_reqs = [req for req in open(abspath(join(dirname(__file__), 'requirements.txt')))]

setup(
    name = "hlsdownload",
    version = "0.0.7",
    author = "Jonas Birme",
    author_email = "jonas.birme@eyevinn.se",
    description = "Download HLS and convert to MP4",
    long_description=long_description,
    license = "MIT",
    install_requires=install_reqs,
    url = "https://github.com/Eyevinn/hls-downloader",
    packages = ['hlsdownload' ],
    entry_points = {
        'console_scripts': [
            'hls-downloader=hlsdownload.downloader:main',
        ]
    }
)

