#!/usr/bin/env python
"""
Verification script for RAG infrastructure setup.
This script checks that all required packages and directory structures are in place.
"""

import sys
from pathlib import Path


def check_packages():
    """Verify all required packages can be imported."""
    print("Checking package imports...")
    packages = {
        "chromadb": "ChromaDB for vector storage",
        "sentence_transformers": "Sentence Transformers for embeddings",
        "hypothesis": "Hypothesis for property-based testing",
    }

    all_ok = True
    for package, description in packages.items():
        try:
            __import__(package)
            print(f"  ✓ {package}: {description}")
        except ImportError as e:
            print(f"  ✗ {package}: FAILED - {e}")
            all_ok = False

    return all_ok


def check_directory_structure():
    """Verify all required directories exist."""
    print("\nChecking directory structure...")

    required_dirs = [
        "offline_chat/rag",
        "tests/rag",
        "tests/rag/unit",
        "tests/rag/property",
        "tests/rag/integration",
        "tests/rag/fixtures",
        "data/rag",
    ]

    all_ok = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists() and path.is_dir():
            print(f"  ✓ {dir_path}")
        else:
            print(f"  ✗ {dir_path}: MISSING")
            all_ok = False

    return all_ok


def check_module_files():
    """Verify all required module files exist."""
    print("\nChecking module files...")

    required_files = [
        "offline_chat/rag/__init__.py",
        "offline_chat/rag/models.py",
        "offline_chat/rag/embedding_generator.py",
        "offline_chat/rag/vector_store.py",
        "offline_chat/rag/document_processor.py",
        "offline_chat/rag/context_retriever.py",
        "offline_chat/rag/prompt_augmenter.py",
        "offline_chat/rag/orchestrator.py",
        "offline_chat/rag/web_scraper.py",
    ]

    all_ok = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists() and path.is_file():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path}: MISSING")
            all_ok = False

    return all_ok


def check_test_files():
    """Verify all required test files exist."""
    print("\nChecking test files...")

    required_files = [
        "tests/rag/__init__.py",
        "tests/rag/unit/__init__.py",
        "tests/rag/property/__init__.py",
        "tests/rag/integration/__init__.py",
        "tests/rag/fixtures/__init__.py",
        "tests/rag/unit/test_embedding_generator.py",
        "tests/rag/unit/test_vector_store.py",
        "tests/rag/unit/test_document_processor.py",
        "tests/rag/unit/test_context_retriever.py",
        "tests/rag/unit/test_prompt_augmenter.py",
        "tests/rag/unit/test_web_scraper.py",
        "tests/rag/property/test_config_properties.py",
        "tests/rag/property/test_chunking_properties.py",
        "tests/rag/property/test_embedding_properties.py",
        "tests/rag/property/test_persistence_properties.py",
        "tests/rag/property/test_retrieval_properties.py",
        "tests/rag/property/test_prompt_properties.py",
        "tests/rag/integration/test_rag_orchestrator.py",
    ]

    all_ok = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists() and path.is_file():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path}: MISSING")
            all_ok = False

    return all_ok


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("RAG Infrastructure Setup Verification")
    print("=" * 70)

    checks = [
        ("Package Imports", check_packages),
        ("Directory Structure", check_directory_structure),
        ("Module Files", check_module_files),
        ("Test Files", check_test_files),
    ]

    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    all_passed = True
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name}: {status}")
        if not result:
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("\n✓ All checks passed! RAG infrastructure is ready.")
        return 0
    else:
        print("\n✗ Some checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
