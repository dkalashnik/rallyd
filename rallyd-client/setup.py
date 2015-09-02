import setuptools
from pip.req import parse_requirements


version = '0.0.1'
setuptools.setup(
    name='rallyd-client',
    version=version,
    description="Client for HTTP API for Rally Benchmark System for OpenStack",
    author="Mirantis",
    author_email="dkalashnik@mirantis.com",
    install_requires=[
        str(ir.req) for ir in parse_requirements('requirements.txt')
    ],
    classifiers=[
        "Environment :: OpenStack",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
    ],
    py_modules=['rallyd_client', 'rallyd_cli'],
    entry_points={
        'console_scripts': [
            'rallyd_cli = rallyd_cli:main'
        ]
    }
)
