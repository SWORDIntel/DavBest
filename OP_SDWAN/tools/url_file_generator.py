import argparse
import configparser
import os
from typing import Optional

def create_url_file(output_path: str, url_target: str,
                    icon_file_path: Optional[str] = None,
                    icon_index: int = 0) -> None:
    """
    Generates a .url file with the specified parameters.

    Args:
        output_path: The full path where the .url file will be saved (e.g., /path/to/shortcut.url).
        url_target: The URL for the shortcut (e.g., http://example.com, file:///C:/data.txt).
        icon_file_path: Optional path to a file containing the icon (e.g., C:\Icons\myicon.ico, \\server\share\icon.dll).
        icon_index: Optional index of the icon within the icon file. Defaults to 0.
    """
    config = configparser.ConfigParser()
    config['InternetShortcut'] = {}
    config['InternetShortcut']['URL'] = url_target

    if icon_file_path:
        config['InternetShortcut']['IconFile'] = icon_file_path
        config['InternetShortcut']['IconIndex'] = str(icon_index)

    try:
        # Ensure the directory for the output path exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")

        with open(output_path, 'w') as configfile:
            config.write(configfile, space_around_delimiters=False)
        print(f"Successfully created .url file: {output_path}")

    except IOError as e:
        print(f"Error writing .url file to {output_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate .url (Internet Shortcut) files.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "output_path",
        type=str,
        help="Full path for the generated .url file (e.g., ./my_shortcut.url)."
    )
    parser.add_argument(
        "url_target",
        type=str,
        help="Target URL for the shortcut (e.g., 'http://example.com', 'file:///C:/doc.txt')."
    )
    parser.add_argument(
        "--icon-file-path",
        type=str,
        default=None,
        help="Optional: Path to the icon file (e.g., 'C:\\path\\to\\icon.ico', '\\\\server\\share\\icon.dll')."
    )
    parser.add_argument(
        "--icon-index",
        type=int,
        default=0,
        help="Optional: Index of the icon in the icon file (default: 0). Only used if --icon-file-path is provided."
    )

    args = parser.parse_args()

    create_url_file(args.output_path, args.url_target, args.icon_file_path, args.icon_index)

    # Example Usage (from command line):
    # python url_file_generator.py my_link.url "http://www.google.com"
    # python url_file_generator.py another_link.url "file:///C:/test.txt" --icon-file-path "\\myserver\icons\some_icon.ico" --icon-index 1
