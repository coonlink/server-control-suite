#!/usr/bin/env python3
"""
Language checker for Server Control Suite.
Displays all available strings in all available languages.
"""
import os
import sys
import json
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utilities import load_language, load_localization_config, AVAILABLE_LANGUAGES
    DIRECT_IMPORT = True
except ImportError:
    DIRECT_IMPORT = False
    # Load language files directly if utilities module is not available
    def load_language(lang_code: str) -> Dict[str, Any]:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        lang_file = os.path.join(base_dir, "localization", f"{lang_code}.json")
        
        if not os.path.exists(lang_file):
            print(f"Error: Language file for '{lang_code}' not found at {lang_file}")
            return {}
        
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                language_data = json.load(f)
                return language_data
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in language file: {lang_file}")
        except Exception as e:
            print(f"Error loading language file '{lang_file}': {e}")
        
        return {}
    
    def load_localization_config() -> Dict[str, Any]:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config", "localization.conf")
        
        config = {
            "DEFAULT_LANGUAGE": "en",
            "MULTI_LANGUAGE_SUPPORT": True,
            "USER_LANGUAGE_SELECTION": True,
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"\'')
                            
                            # Convert boolean values
                            if value.lower() == 'true':
                                value = True
                            elif value.lower() == 'false':
                                value = False
                            
                            config[key] = value
                
                print("Localization config loaded successfully")
            except Exception as e:
                print(f"Error loading localization config: {e}")
        else:
            print(f"Warning: Localization config file not found at {config_path}")
        
        return config
    
    # Define available languages
    AVAILABLE_LANGUAGES = ["en", "ru"]

def flatten_dict(d, parent_key='', sep='.'):
    """Flatten a nested dictionary with dot notation keys."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def get_text_by_key(lang_data, key):
    """Get text from language data by dot notation key."""
    keys = key.split('.')
    value = lang_data
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return None
    
    return value

def print_language_comparison():
    """Print all strings in all available languages."""
    print("=" * 80)
    print(f"Server Control Suite - Language Checker")
    print("=" * 80)
    
    # Load config
    config = load_localization_config()
    default_language = config.get("DEFAULT_LANGUAGE", "en")
    
    print(f"Default language: {default_language}")
    print(f"Available languages: {', '.join(AVAILABLE_LANGUAGES)}")
    print(f"Multi-language support: {'Enabled' if config.get('MULTI_LANGUAGE_SUPPORT', False) else 'Disabled'}")
    print(f"User language selection: {'Enabled' if config.get('USER_LANGUAGE_SELECTION', False) else 'Disabled'}")
    
    print("\n" + "=" * 80)
    print("Language String Comparison")
    print("=" * 80 + "\n")
    
    # Load all languages
    language_data = {}
    all_keys = set()
    
    for lang_code in AVAILABLE_LANGUAGES:
        language_data[lang_code] = load_language(lang_code)
        flattened = flatten_dict(language_data[lang_code])
        all_keys.update(flattened.keys())
    
    # Sort keys for consistent output
    all_keys = sorted(all_keys)
    
    # Print side by side comparison
    header = "Key".ljust(40)
    for lang_code in AVAILABLE_LANGUAGES:
        header += f"| {lang_code.upper()}".ljust(40)
    print(header)
    print("-" * (40 * (len(AVAILABLE_LANGUAGES) + 1)))
    
    for key in all_keys:
        row = key.ljust(40)
        for lang_code in AVAILABLE_LANGUAGES:
            value = get_text_by_key(language_data[lang_code], key)
            value_str = str(value)[:36] + "..." if value and len(str(value)) > 39 else str(value)
            row += f"| {value_str or '---'}".ljust(40)
        print(row)
    
    # Check for missing keys
    print("\n" + "=" * 80)
    print("Missing Keys Analysis")
    print("=" * 80 + "\n")
    
    for lang_code in AVAILABLE_LANGUAGES:
        missing_keys = []
        
        for key in all_keys:
            if get_text_by_key(language_data[lang_code], key) is None:
                missing_keys.append(key)
        
        if missing_keys:
            print(f"Language {lang_code.upper()} is missing {len(missing_keys)} keys:")
            for key in missing_keys:
                print(f"  - {key}")
        else:
            print(f"Language {lang_code.upper()} has all keys.")
        
        print()

if __name__ == "__main__":
    print_language_comparison() 