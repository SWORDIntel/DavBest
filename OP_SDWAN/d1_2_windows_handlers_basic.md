# Windows ShellExecute Handlers for .url Files (Basic)

This document describes the common behaviors of Windows ShellExecute when activating `.url` files, specifically focusing on how it invokes default handlers for standard URL schemes.

## ShellExecute and .url Activation

When a user activates a `.url` file (e.g., by double-clicking it), Windows uses the `ShellExecute` API function (or similar shell mechanisms) to handle the file. The primary action is determined by the content of the `.url` file, specifically the `URL=` key within the `[InternetShortcut]` section.

## Default Handlers for Standard URL Schemes

`ShellExecute` relies on the registered handlers for different URL schemes to process the URL specified in the `.url` file.

1.  **`http://` and `https://` Schemes:**
    *   **Handler:** The system's default web browser.
    *   **Behavior:** When the `URL=` key points to an `http://` or `https://` address (e.g., `URL=http://www.example.com`), `ShellExecute` launches the default web browser and instructs it to navigate to the specified web address.

2.  **`file://` Scheme:**
    *   **Handler:** Typically File Explorer or an application associated with the file type specified in the path.
    *   **Behavior:**
        *   If the `URL=` key points to a directory (e.g., `URL=file:///C:/Users/`), File Explorer will open that directory.
        *   If the `URL=` key points to a specific file (e.g., `URL=file:///C:/path/to/document.pdf`), `ShellExecute` will attempt to open that file with its default registered application (e.g., Adobe Reader for a `.pdf` file).
        *   UNC paths (e.g., `file://\\server\share\file.txt`) are also handled, typically by attempting to access the network resource.

## Summary

In its basic operation, `ShellExecute` interprets the `URL=` value in a `.url` file and passes it to the appropriate system-registered handler based on the URL's scheme. This allows `.url` files to act as shortcuts to web pages, local files, and network resources.
