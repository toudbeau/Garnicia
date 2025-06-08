# Garnicia

Garnicia is a lightweight, open-source note-taking application built with Python and GTK 3. It allows users to manage plain text notes within a selected folder, offering features like inline renaming, auto-saving with SQLite backups, and a clean, user-friendly interface.

## Features

- Folder-based organization
- Integrated text editor with word wrap
- Inline renaming of notes
- Auto-save with SQLite backup
- User-friendly GTK 3 interface
- Customizable editor font and size

## Dependencies

- python3-gi
- gir1.2-gtk-3.0
- imagemagick  # needed for the build script

## Installation

# Using the build script

1. Run the build script:

   ./build_garnicia.sh

   This will generate a `.deb` package in the current directory.

2. Install the package:

   sudo apt install ./Garnicia_1.0_all.deb

   Replace `Garnicia_1.0_all.deb` with the actual filename if it differs.

# Manual installation

1. Build the `.deb` package:

   dpkg-deb --build build

   This will create a `build.deb` file in the current directory.

2. Install the package:

   sudo apt install ./build.deb

After installation, you can launch Garnicia from your applications menu or by running `Garnicia` in the terminal.


## Usage

1. Launch Garnicia from your applications menu or by running `Garnicia` in the terminal.

2. Click the folder icon to select a directory where your notes will be stored.

3. Use the '+' button to create a new note. Enter a filename (lowercase, no spaces or special characters).

4. Select a note from the list to view or edit its contents in the text editor.

5. Click the save icon to save changes to the selected note.
6. Use the font drop-down and size spinner in the header to adjust the editor's appearance.

7. To rename a note, double-click its name in the list and enter a new name.

8. To delete a note, select it and click the trash icon. Confirm the deletion when prompted.

9. Unsaved changes are indicated with an asterisk (*) next to the note's name.

10. Garnicia automatically saves your work in a temporary journal. Ensure you click the save icon to permanently save changes to the file.


## License

This project is licensed under the GNU General Public License v3.0 (GPLv3).
See the [LICENSE](LICENSE) file for details.

