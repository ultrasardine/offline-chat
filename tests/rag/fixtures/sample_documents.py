"""
Sample documents and test data for RAG testing.
"""

# Sample web content for testing
SAMPLE_WEB_CONTENT = """
# Python Programming Guide

Python is a high-level, interpreted programming language known for its simplicity and readability.

## Key Features
- Easy to learn and use
- Extensive standard library
- Dynamic typing
- Object-oriented programming support

## Getting Started
To start programming in Python, you need to install Python from python.org.
"""

# Sample database rows for testing
SAMPLE_DATABASE_ROWS = [
    {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com",
        "department": "Engineering"
    },
    {
        "id": 2,
        "name": "Jane Smith",
        "email": "jane@example.com",
        "department": "Marketing"
    },
    {
        "id": 3,
        "name": "Bob Johnson",
        "email": "bob@example.com",
        "department": "Sales"
    }
]

# Sample queries for testing
SAMPLE_QUERIES = [
    "What is Python?",
    "How do I get started with Python?",
    "Tell me about Python's features",
    "Who works in the Engineering department?",
    "What is Jane's email address?"
]
