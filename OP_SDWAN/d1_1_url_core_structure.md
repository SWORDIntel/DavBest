# .url File Core Structure

This document outlines the fundamental structure of `.url` files, primarily used by Windows to create internet shortcuts.

## Basic Syntax and Mandatory Sections

A `.url` file is a plain text file formatted similarly to an INI file. The core and mandatory section for it to function as an internet shortcut is `[InternetShortcut]`.

## `URL=` Key

Within the `[InternetShortcut]` section, the `URL=` key is essential.
- **Function:** It specifies the URL that the shortcut will open. This can be a web address (e.g., `http://www.example.com`), a file path (e.g., `file:///C:/path/to/file.txt`), or other URL schemes recognized by the system.
- **Example:**
  ```ini
  [InternetShortcut]
  URL=http://www.example.com
  ```
This is the minimal requirement for a functional `.url` file.
