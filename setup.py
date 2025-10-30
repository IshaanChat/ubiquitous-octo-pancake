from setuptools import setup, find_packages

setup(
    name="servicenow-mcp",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "python-dotenv==1.0.0",
        "requests==2.31.0",
        "httpx==0.25.1",
        "pydantic>=2.4.2",
        "pydantic-settings>=2.0.0",
        "pysnow==0.7.17",
        "PyYAML>=6.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "isort>=5.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "snow-mcp=main:main",
        ],
    },
)