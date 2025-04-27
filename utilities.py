#!/usr/bin/env python3
"""
Utility functions for the server control bot.
Handles language loading, preferences, and other helper functions.
"""
import os
import json
import logging
from typing import Dict, Any, Optional

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Default language
DEFAULT_LANGUAGE = "en"
# Available languages
AVAILABLE_LANGUAGES = ["en", "ru"]
# Path to localization config
LOCALIZATION_CONFIG_PATH = os.path.join(BASE_DIR, "config", "localization.conf")
# Path to language files
LANGUAGE_DIR = os.path.join(BASE_DIR, "localization")
# User preferences file
USER_PREFERENCES_FILE = os.path.join(BASE_DIR, "user_preferences.json")

# Cache for loaded languages
_language_cache = {}
# Default localization config
_localization_config = {
    "DEFAULT_LANGUAGE": "en",
    "MULTI_LANGUAGE_SUPPORT": True,
    "USER_LANGUAGE_SELECTION": True,
    "LANG_BUTTON_EN": "🇬🇧 English",
    "LANG_BUTTON_RU": "🇷🇺 Русский",
    "LANG_MENU_TITLE": "Select language / Выберите язык:",
    "LANG_SELECTED_EN": "Language set to English",
    "LANG_SELECTED_RU": "Язык изменен на Русский"
}

def load_localization_config() -> Dict[str, Any]:
    """
    Load localization configuration from file
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    global _localization_config
    
    if os.path.exists(LOCALIZATION_CONFIG_PATH):
        try:
            config = {}
            with open(LOCALIZATION_CONFIG_PATH, 'r', encoding='utf-8') as f:
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
            
            # Update default config with values from file
            _localization_config.update(config)
            logging.info("Localization config loaded successfully")
        except Exception as e:
            logging.error(f"Error loading localization config: {e}")
    else:
        logging.warning(f"Localization config file not found at {LOCALIZATION_CONFIG_PATH}")
    
    return _localization_config

def load_language(lang_code: str) -> Dict[str, Any]:
    """
    Load language file for the specified language code
    
    Args:
        lang_code (str): Language code (e.g., 'en', 'ru')
        
    Returns:
        Dict[str, Any]: Language dictionary or empty dict if not found
    """
    global _language_cache
    
    # Check if language is already in cache
    if lang_code in _language_cache:
        return _language_cache[lang_code]
    
    lang_file = os.path.join(LANGUAGE_DIR, f"{lang_code}.json")
    
    if not os.path.exists(lang_file):
        logging.error(f"Language file for '{lang_code}' not found at {lang_file}")
        # If the requested language is not available, return empty dict
        return {}
    
    try:
        with open(lang_file, 'r', encoding='utf-8') as f:
            language_data = json.load(f)
            _language_cache[lang_code] = language_data
            logging.info(f"Language '{lang_code}' loaded successfully")
            return language_data
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in language file: {lang_file}")
    except Exception as e:
        logging.error(f"Error loading language file '{lang_file}': {e}")
    
    return {}

def get_user_language(user_id: int) -> str:
    """
    Get the preferred language for a user
    
    Args:
        user_id (int): User's Telegram ID
        
    Returns:
        str: Language code
    """
    config = load_localization_config()
    default_lang = config.get("DEFAULT_LANGUAGE", DEFAULT_LANGUAGE)
    
    # If multi-language support is disabled, return default language
    if not config.get("MULTI_LANGUAGE_SUPPORT", True):
        return default_lang
    
    # Load user preferences
    user_preferences = load_user_preferences()
    return user_preferences.get(str(user_id), {}).get("language", default_lang)

def set_user_language(user_id: int, lang_code: str) -> bool:
    """
    Set the preferred language for a user
    
    Args:
        user_id (int): User's Telegram ID
        lang_code (str): Language code to set
        
    Returns:
        bool: True if successful, False otherwise
    """
    config = load_localization_config()
    
    # If multi-language support is disabled, don't change preferences
    if not config.get("MULTI_LANGUAGE_SUPPORT", True):
        return False
    
    # Check if language is available
    if lang_code not in AVAILABLE_LANGUAGES:
        return False
    
    # Load current preferences
    user_preferences = load_user_preferences()
    
    # Update language preference
    if str(user_id) not in user_preferences:
        user_preferences[str(user_id)] = {}
    
    user_preferences[str(user_id)]["language"] = lang_code
    
    # Save preferences
    return save_user_preferences(user_preferences)

def load_user_preferences() -> Dict[str, Dict[str, Any]]:
    """
    Load user preferences from file
    
    Returns:
        Dict[str, Dict[str, Any]]: User preferences dictionary
    """
    if not os.path.exists(USER_PREFERENCES_FILE):
        return {}
    
    try:
        with open(USER_PREFERENCES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in user preferences file: {USER_PREFERENCES_FILE}")
    except Exception as e:
        logging.error(f"Error loading user preferences: {e}")
    
    return {}

def save_user_preferences(preferences: Dict[str, Dict[str, Any]]) -> bool:
    """
    Save user preferences to file
    
    Args:
        preferences (Dict[str, Dict[str, Any]]): User preferences dictionary
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(USER_PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(preferences, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving user preferences: {e}")
        return False

def get_text(key: str, lang_code: str = DEFAULT_LANGUAGE) -> str:
    """
    Get text from language file by key
    
    Args:
        key (str): Text key in dot notation (e.g., 'main.welcome')
        lang_code (str, optional): Language code. Defaults to DEFAULT_LANGUAGE.
        
    Returns:
        str: Text value or key if not found
    """
    # Load the language file
    lang_data = load_language(lang_code)
    
    # If language not found, try default language
    if not lang_data and lang_code != DEFAULT_LANGUAGE:
        lang_data = load_language(DEFAULT_LANGUAGE)
    
    # Split the key by dots to navigate nested dictionaries
    keys = key.split('.')
    value = lang_data
    
    # Traverse the nested dictionary
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            # Key not found, return the key itself
            return key
    
    # If value is not a string (e.g., it's a dictionary), return the key
    if not isinstance(value, str):
        return key
    
    return value

# Load the localization config at module import
load_localization_config() 