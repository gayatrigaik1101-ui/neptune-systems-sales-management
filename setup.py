"""
Neptune Systems - Sales Management System
Package Setup Configuration
"""

from setuptools import setup, find_packages

setup(
    name="neptune-systems-sales-management",
    version="1.0.0",
    description="Google Workspace + Python Sales Management Automation for Neptune Systems",
    author="Neptune Systems Development Team",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "streamlit>=1.35.0",
        "pandas>=2.0.0",
        "gspread>=6.0.0",
        "google-api-python-client>=2.100.0",
        "google-auth>=2.20.0",
        "google-auth-oauthlib>=1.2.0",
        "google-auth-httplib2>=0.2.0",
        "python-dotenv>=1.0.0",
        "bcrypt>=4.1.0",
        "pytest>=8.0.0",
        "openpyxl>=3.1.0",
    ],
    entry_points={
        "console_scripts": [
            "neptune-sales=app.main:main",
        ],
    },
)
