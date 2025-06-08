#!/usr/bin/env python3
# Garnicia - A GTK-based note-taking application
# Copyright (C) 2025 Arthur Dubeux Estevam
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import sqlite3
import sys
import traceback

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
except ModuleNotFoundError:
    sys.stderr.write(
        "Error: PyGObject is required.\n"
        "Install the 'python3-gi' and 'gir1.2-gtk-3.0' packages.\n"
    )
    sys.exit(1)

# Configuration paths
CONFIG_FOLDER = os.path.expanduser('~/.config/txtnotes')
CONFIG_FILE = os.path.join(CONFIG_FOLDER, 'folder')
DB_FILE = os.path.join(CONFIG_FOLDER, 'journal.db')
DEBUG_FILE = os.path.join(CONFIG_FOLDER, 'debug.log')

# Ensure config directory and debug log
os.makedirs(CONFIG_FOLDER, exist_ok=True)
with open(DEBUG_FILE, 'w', encoding='utf-8') as df:
    df.write('=== Garnicia Debug Log ===\n')

# Exception hook logs crashes to debug file
def excepthook(exc_type, exc_value, exc_tb):
    with open(DEBUG_FILE, 'a', encoding='utf-8') as df:
        traceback.print_exception(exc_type, exc_value, exc_tb, file=df)
    sys.__excepthook__(exc_type, exc_value, exc_tb)
sys.excepthook = excepthook

class NotesWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title('Garnicia')
        self.set_default_size(800, 600)

        # Initialize DB
        try:
            self.db = sqlite3.connect(DB_FILE)
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS journal(
                    filename TEXT PRIMARY KEY,
                    content TEXT
                )''')
            self.db.commit()
        except Exception:
            traceback.print_exc(file=open(DEBUG_FILE, 'a'))
            self.db = None

        # State
        self.folder = None
        self.current_file = None
        self.dirty_files = set()

        # Header: folder, save, plus on left; trash on right
        header = Gtk.HeaderBar(show_close_button=True, title='Garnicia')
        self.set_titlebar(header)

        btn_open = Gtk.Button.new_from_icon_name('folder-open-symbolic', Gtk.IconSize.BUTTON)
        btn_open.connect('clicked', self.on_open_folder)
        header.pack_start(btn_open)

        btn_save = Gtk.Button.new_from_icon_name('media-floppy-symbolic', Gtk.IconSize.BUTTON)
        btn_save.connect('clicked', self.on_save)
        header.pack_start(btn_save)

        btn_new = Gtk.Button.new_from_icon_name('list-add-symbolic', Gtk.IconSize.BUTTON)
        btn_new.connect('clicked', self.on_new_note)
        header.pack_start(btn_new)

        btn_delete = Gtk.Button.new_from_icon_name('user-trash-symbolic', Gtk.IconSize.BUTTON)
        btn_delete.connect('clicked', self.on_delete_note)
        header.pack_end(btn_delete)

        # Layout: split list and text view
        paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self.add(paned)

        # Notes list with inline edit
        self.liststore = Gtk.ListStore(str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        renderer = Gtk.CellRendererText()
        renderer.set_property('editable', True)
        renderer.connect('edited', self.on_rename)
        renderer.connect('editing-started', self.on_start_inline_edit)
        self.column = Gtk.TreeViewColumn('Notes', renderer, text=0)
        self.treeview.append_column(self.column)
        self.selection = self.treeview.get_selection()
        self.selection_handler_id = self.selection.connect('changed', self.on_note_selected)
        scroll_list = Gtk.ScrolledWindow()
        scroll_list.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_list.add(self.treeview)
        paned.pack1(scroll_list, resize=True, shrink=False)
        paned.set_position(200)

        # Text editor
        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        for side in ('left', 'right', 'top', 'bottom'):
            getattr(self.textview, f'set_{side}_margin')(10)
        self.textbuffer = self.textview.get_buffer()
        self.changed_id = self.textbuffer.connect('changed', self.on_text_changed)
        scroll_text = Gtk.ScrolledWindow()
        scroll_text.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_text.add(self.textview)
        paned.pack2(scroll_text, resize=True, shrink=True)

        # Load last folder and populate
        self.load_last_folder()
        self.show_all()

    def enforce_lowercase(self, entry):
        text = entry.get_text()
        lower = text.lower()
        if text != lower:
            pos = entry.get_position()
            entry.set_text(lower)
            entry.set_position(pos)

    def on_start_inline_edit(self, renderer, editable, path):
        editable.connect('changed', lambda e: self.enforce_lowercase(e))

    def show_error(self, msg):
        with open(DEBUG_FILE, 'a', encoding='utf-8') as df:
            df.write(f'ERROR: {msg}\n')
        dlg = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text='Error')
        dlg.format_secondary_text(msg)
        dlg.run(); dlg.destroy()

    def load_last_folder(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as cf:
                    p = cf.read().strip()
                if os.path.isdir(p):
                    self.folder = p
        except Exception as e:
            self.show_error(f'Config load failed: {e}')
        # Clear text when loading folder
        self.current_file = None
        self.textbuffer.set_text('')
        self.dirty_files.clear()
        self.refresh_list()

    def save_folder(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as cf:
                cf.write(self.folder or '')
        except Exception as e:
            self.show_error(f'Config save failed: {e}')

    def on_open_folder(self, widget):
        dlg = Gtk.FileChooserDialog(
            title='Select Notes Folder', transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER)
        dlg.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dlg.set_current_folder(self.folder or os.path.expanduser('~'))
        if dlg.run() == Gtk.ResponseType.OK:
            self.folder = dlg.get_current_folder()
            self.save_folder()
            # Clear editor and state when changing folder
            self.current_file = None
            self.textbuffer.set_text('')
            self.dirty_files.clear()
            self.refresh_list()
        dlg.destroy()

    def on_new_note(self, widget):
        if not self.folder:
            return
        dlg = Gtk.Dialog(title='New Note', transient_for=self)
        dlg.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                        Gtk.STOCK_OK, Gtk.ResponseType.OK)
        area = dlg.get_content_area()
        area.set_border_width(10)
        entry = Gtk.Entry()
        entry.set_placeholder_text('Filename')
        entry.connect('changed', lambda e: self.enforce_lowercase(e))
        area.add(entry)
        entry.show()
        if dlg.run() == Gtk.ResponseType.OK:
            name = entry.get_text().strip().lower()
            if name:
                try:
                    open(os.path.join(self.folder, name), 'a').close()
                except Exception as e:
                    self.show_error(f'New note failed: {e}')
                self.refresh_list()
        dlg.destroy()

    def on_delete_note(self, widget):
        model, it = self.selection.get_selected()
        if not it or not self.folder:
            return
        raw = model[it][0]
        name = raw.lstrip('*')
        path = os.path.join(self.folder, name)
        if not os.path.exists(path):
            return
        dlg = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text='Delete Note?')
        disp = name if len(name) <= 20 else name[:20] + '...'
        dlg.format_secondary_text(f"Delete '{disp}' permanently?")
        if dlg.run() == Gtk.ResponseType.OK:
            try:
                os.remove(path)
            except Exception as e:
                self.show_error(f'Delete failed: {e}')
            else:
                self.current_file = None
                self.textbuffer.set_text('')
                self.dirty_files.clear()
                self.selection.unselect_all()
                self.refresh_list()
        dlg.destroy()

    def on_note_selected(self, selection):
        try:
            model, it = selection.get_selected()
            if not it or not self.folder:
                return
            raw = model[it][0]
            name = raw.lstrip('*')
            path = os.path.join(self.folder, name)
            if self.db:
                cur = self.db.cursor()
                cur.execute('SELECT content FROM journal WHERE filename=?', (name,))
                row = cur.fetchone()
                text = row[0] if row else open(path, 'r', encoding='utf-8').read()
            else:
                text = open(path, 'r', encoding='utf-8').read()
            self.current_file = path
            self.textbuffer.handler_block(self.changed_id)
            self.textbuffer.set_text(text)
            self.textbuffer.handler_unblock(self.changed_id)
        except Exception:
            traceback.print_exc(file=open(DEBUG_FILE, 'a'))

    def on_text_changed(self, buf):
        if not self.current_file or not self.db:
            return
        name = os.path.basename(self.current_file)
        content = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        try:
            self.db.execute('INSERT OR REPLACE INTO journal VALUES(?,?)', (name, content))
            self.db.commit()
        except Exception:
            pass
        if name not in self.dirty_files:
            self.dirty_files.add(name)
        self.refresh_list()

    def on_save(self, widget):
        if not self.current_file:
            return
        name = os.path.basename(self.current_file)
        text = self.textbuffer.get_text(
            self.textbuffer.get_start_iter(),
            self.textbuffer.get_end_iter(), True)
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(text)
            if self.db:
                self.db.execute('DELETE FROM journal WHERE filename=?', (name,))
                self.db.commit()
            self.dirty_files.discard(name)
            self.refresh_list()
        except Exception as e:
            self.show_error(f'Save failed: {e}')

    def on_rename(self, widget, path, new_text):
        old_display = self.liststore[path][0]
        old_name = old_display.lstrip('*')
        new_name = new_text.strip().lower()
        if new_name == old_name:
            return
        if not new_name or '/' in new_name or new_name.startswith('*'):
            return
        existing = [f.lower() for f in os.listdir(self.folder)]
        if new_name in existing:
            self.show_error('A file with that name already exists')
            return
        old_path = os.path.join(self.folder, old_name)
        new_path = os.path.join(self.folder, new_name)
        try:
            os.rename(old_path, new_path)
            if self.db:
                cur = self.db.cursor()
                cur.execute('SELECT content FROM journal WHERE filename=?', (old_name,))
                row = cur.fetchone()
                if row:
                    content = row[0]
                    cur.execute('DELETE FROM journal WHERE filename=?', (old_name,))
                    cur.execute('INSERT INTO journal VALUES(?,?)', (new_name, content))
                    self.db.commit()
            self.current_file = new_path if self.current_file and self.current_file.endswith(old_name) else self.current_file
            self.refresh_list()
        except Exception as e:
            self.show_error(f'Rename failed: {e}')

    def refresh_list(self):
        try:
            self.selection.disconnect(self.selection_handler_id)
        except Exception:
            pass
        self.liststore.clear()
        if self.folder:
            files = sorted(
                [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f))],
                key=str.lower
            )
            for f in files:
                prefix = '*' if f in self.dirty_files else ''
                self.liststore.append([f'{prefix}{f.lower()}'])
        self.selection_handler_id = self.selection.connect('changed', self.on_note_selected)
        self.column.set_title('Notes')

class NotesApp(Gtk.Application):
    def __init__(self): super().__init__(application_id='org.local.garnicia')
    def do_startup(self): Gtk.Application.do_startup(self)
    def do_activate(self): NotesWindow(self).show_all()

if __name__=='__main__': sys.exit(NotesApp().run(None))

