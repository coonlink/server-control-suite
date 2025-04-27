# Localization System

The Server Control Suite includes a multi-language support system that allows the bot to communicate with users in their preferred language. This document describes how to use and customize the localization features.

## Languages Support

Currently, the system supports the following languages:

- 🇬🇧 **English** (en) - Default language
- 🇷🇺 **Russian** (ru)

## Configuration

The localization system is configured through the file `config/localization.conf`. Here you can set the default language, enable or disable multi-language support, and customize language selection buttons.

```
# Default language to use
DEFAULT_LANGUAGE="en"

# Enable multi-language support (true/false)
MULTI_LANGUAGE_SUPPORT=true

# Allow users to select language via bot commands (true/false)
USER_LANGUAGE_SELECTION=true

# Language selection button text
LANG_BUTTON_EN="🇬🇧 English"
LANG_BUTTON_RU="🇷🇺 Русский"

# Language selection menu title
LANG_MENU_TITLE="Select language / Выберите язык:"

# Language selection success messages
LANG_SELECTED_EN="Language set to English"
LANG_SELECTED_RU="Язык изменен на Русский"
```

## Language Files

The language strings are stored in JSON files in the `localization` directory. Each language has its own file named with its language code (e.g. `en.json`, `ru.json`).

The JSON files contain nested objects with the strings organized by categories. For example:

```json
{
  "main": {
    "welcome": "🤖 Server Control Panel v1.0",
    "new_features": "🆕 New features:"
  },
  "buttons": {
    "status": "📊 Status",
    "processes": "🔄 Processes"
  }
}
```

## Usage

### User Interface

Users can change the language by using the `/language` command in the Telegram bot. This will display a menu with available language options.

### Adding New Strings

To add new strings to the localization system:

1. Add the new strings to all language files in the `localization` directory.
2. Organize the strings in appropriate categories (sections).
3. Use the same keys in all language files.

For example, if you want to add a new button label:

```json
// In en.json
{
  "buttons": {
    "new_button": "New Feature"
  }
}

// In ru.json
{
  "buttons": {
    "new_button": "Новая Функция"
  }
}
```

### Using Localized Strings in Code

In the bot code, you can access localized strings using the `_()` function:

```python
# Get a localized string for a specific user
welcome_text = _("main.welcome", user_id)

# Get a button label for a user
button_label = _("buttons.status", user_id)
```

The function will automatically use the user's preferred language if multi-language support is enabled.

## Adding a New Language

To add a new language:

1. Create a new JSON file in the `localization` directory with the language code as the filename (e.g. `de.json` for German).
2. Copy the structure from an existing language file.
3. Translate all strings to the new language.
4. Add the new language code to the `AVAILABLE_LANGUAGES` list in `utilities.py`.
5. Add button text in `config/localization.conf`:
   ```
   LANG_BUTTON_DE="🇩🇪 Deutsch"
   LANG_SELECTED_DE="Sprache auf Deutsch eingestellt"
   ```
6. Update the language selection keyboard in `server_control_bot.py` to include the new language.

## Testing

You can test the localization system using the `check_language.py` script, which displays all available strings in all languages and identifies any missing translations.

```bash
python3 check_language.py
```

## Contributions

When contributing to the project, please:

- Add new strings to all language files
- Maintain consistent key naming
- Use descriptive category and key names

## Fallback Behavior

If a string is not found in the user's preferred language, the system will:

1. Try to find the string in the default language
2. If still not found, return the key itself as a fallback 