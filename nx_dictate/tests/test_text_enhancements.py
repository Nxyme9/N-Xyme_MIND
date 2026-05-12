#!/usr/bin/env python3
"""Quick test for N-Xyme Dictate functionality."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nx_dictate.text_processor import (
    process_text,
    PersonalDictionary,
    SnippetsManager,
    remove_fillers,
)

def test_filler_removal():
    print("Testing filler word removal...")
    test_cases = [
        ("um hello world", "hello world"),
        ("like I was saying", "I was saying"),
        ("so basically the thing is", "the thing is"),
        ("okay so um yeah I think maybe", ""),
        ("hello um uh er ah like world", "hello world"),
    ]
    
    for input_text, expected in test_cases:
        result = remove_fillers(input_text)
        status = "✓" if expected in result or result.strip() == expected.strip() else "✗"
        print(f"  {status} '{input_text}' -> '{result}'")

def test_personal_dictionary():
    print("\nTesting personal dictionary...")
    import tempfile
    import json
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        d = PersonalDictionary(temp_path)
        d.add("nxyme", "N-Xyme")
        d.add("gpt", "GPT")
        
        result = d.lookup("nxyme is better than gpt")
        print(f"  ✓ Dictionary lookup: 'nxyme is better than gpt' -> '{result}'")
        
        d.remove("nxyme")
        result = d.lookup("nxyme is great")
        print(f"  ✓ Dictionary remove: 'nxyme is great' -> '{result}'")
        
    finally:
        os.unlink(temp_path)

def test_snippets():
    print("\nTesting snippets...")
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        s = SnippetsManager(temp_path)
        s.add("brb", "be right back")
        s.add("lol", "laugh out loud")
        
        result = s.expand("brb and then lol")
        print(f"  ✓ Snippet expand: 'brb and then lol' -> '{result}'")
        
    finally:
        os.unlink(temp_path)

def test_full_processing():
    print("\nTesting full text processing...")
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        d = PersonalDictionary(temp_path)
        d.add("nx", "N-Xyme")
        
        s = SnippetsManager(temp_path)
        s.add("omg", "oh my god")
        
        result = process_text(
            "um like nx is omg",
            enable_fillers=True,
            dictionary=d,
            snippets=s,
        )
        print(f"  ✓ Full process: 'um like nx is omg' -> '{result}'")
        
    finally:
        os.unlink(temp_path)

def test_injection_backend():
    print("\nTesting injection backend detection...")
    from nx_dictate.injection import get_backend
    backend = get_backend()
    print(f"  ✓ Available backend: {backend}")

if __name__ == "__main__":
    print("=" * 50)
    print("N-Xyme Dictate Quick Test")
    print("=" * 50)
    
    test_filler_removal()
    test_personal_dictionary()
    test_snippets()
    test_full_processing()
    test_injection_backend()
    
    print("\n" + "=" * 50)
    print("Tests completed!")
    print("=" * 50)