#!/usr/bin/env python3
"""
Simple test script to check if all required modules can be imported.
This helps identify missing dependencies before PyInstaller build.
"""

import sys
import os

def test_import(module_name, description=""):
    try:
        __import__(module_name)
        print(f"✓ {module_name} - OK {description}")
        return True
    except ImportError as e:
        print(f"✗ {module_name} - FAILED: {e}")
        return False
    except Exception as e:
        print(f"⚠ {module_name} - ERROR: {e}")
        return False

def main():
    print("Testing imports for PyInstaller build...")
    print("=" * 50)
    
    # Test basic Python modules
    test_import('os')
    test_import('sys')
    test_import('subprocess')
    test_import('threading')
    test_import('time')
    
    # Test PySide6
    test_import('PySide6', '(Qt for GUI)')
    test_import('PySide6.QtCore')
    test_import('PySide6.QtGui')
    test_import('PySide6.QtWidgets')
    
    # Test PyTorch and related
    test_import('torch', '(PyTorch)')
    test_import('torchaudio', '(PyTorch audio)')
    
    # Test Whisper
    test_import('whisper', '(OpenAI Whisper)')
    
    # Test other dependencies
    test_import('numpy', '(Numerical computing)')
    test_import('regex', '(Regular expressions)')
    
    # Test local modules
    test_import('AutoCaptions_gui', '(Local GUI module)')
    test_import('AutoCaptions', '(Local backend module)')
    
    print("=" * 50)
    print("Import test complete!")

if __name__ == "__main__":
    main()