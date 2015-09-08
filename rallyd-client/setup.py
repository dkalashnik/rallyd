import setuptools
from pip.req import parse_requirements

try:
    from pip.download import PipSession
    requirements = [
        str(ir.req) for ir in parse_requirements('requirements.txt',
                                                 session=PipSession())]
except ImportError:
    requirements = [
        str(ir.req) for ir in parse_requirements('requirements.txt')]


version = '1.0.0'
setuptools.setup(
    name='rallyd-client',
    version=version,
    description="Client for HTTP API for Rally Benchmark System for OpenStack",
    author="Mirantis",
    author_email="dkalashnik@mirantis.com",
    install_requires=requirements,
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
