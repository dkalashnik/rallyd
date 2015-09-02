import setuptools
from pip import download
from pip.req import parse_requirements


version = '0.0.1'
setuptools.setup(
    name='rallyd',
    version=version,
    description="HTTP API for Rally Benchmark System for OpenStack",
    author="Mirantis",
    author_email="dkalashnik@mirantis.com",
    install_requires=[
        str(ir.req) for ir in parse_requirements('requirements.txt',
                                                 session=download.PipSession())
    ],
    classifiers=[
        "Environment :: OpenStack",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
    ],
    py_modules=['rallyd'],
    entry_points={
        'console_scripts':[
            'rallyd = rallyd:main'
        ]
    }
)
