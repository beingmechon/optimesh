import os

from setuptools import find_packages, setup

# https://packaging.python.org/single_source_version/
base_dir = os.path.abspath(os.path.dirname(__file__))
about = {}
with open(os.path.join(base_dir, "optimesh", "__about__.py"), "rb") as f:
    exec(f.read(), about)


setup(
    name="optimesh",
    version=about["__version__"],
    author=about["__author__"],
    author_email=about["__author_email__"],
    packages=find_packages(),
    description="Mesh optimization/smoothing",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url=about["__website__"],
    license=about["__license__"],
    platforms="any",
    install_requires=[
        "meshio < 4",
        "meshplex < 0.13.0",
        "numpy",
        "quadpy",
        "termplotlib",
    ],
    python_requires=">=3.5",
    extras_require={"all": ["matplotlib"], "png": ["matplotlib"]},
    classifiers=[
        about["__status__"],
        about["__license__"],
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering",
        "Topic :: Utilities",
    ],
    entry_points={
        "console_scripts": [
            "optimesh = optimesh.cli:main",
            "optimesh-info = optimesh.cli:info",
        ]
    },
)