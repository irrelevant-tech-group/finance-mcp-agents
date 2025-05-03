from setuptools import setup, find_packages

setup(
    name="finance-ai",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "typer>=0.9.0",
        "rich>=13.3.5",
        "supabase>=2.0.0",
        "pinecone-client>=2.2.1",
        "anthropic>=0.5.0",
        "langchain>=0.0.267",
        "langchain-anthropic>=0.0.1", 
        "pytesseract>=0.3.10",
        "pdf2image>=1.16.3",
        "pypdf>=3.15.1",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
    ],
    entry_points={
        "console_scripts": [
            "financeai=cli.main:app",
        ],
    },
)