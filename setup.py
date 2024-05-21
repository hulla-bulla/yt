from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read()
    
setup(
    name = 'yt',
    version = '0.0.12',
    author = 'HullaBulla',
    author_email = 'hullabulla666@gmail.com',
    description = 'Youtube download helper using yt-dlp and ffmpeg',
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = 'https://github.com/hulla-bulla/yt',
    py_modules = ['yt', 'app'],
    packages = find_packages(),
    install_requires = [requirements],
    python_requires='>=3.10',
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "Operating System :: Windows",
    ],
    entry_points = '''
        [console_scripts]
        yt=yt:cli
    '''
)