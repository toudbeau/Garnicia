#exec: chmod +x build_garnicia.sh
#run: ./build_garnicia.sh

#!/usr/bin/env bash
set -e

# Variables
PKG_NAME="Garnicia"
PKG_VERSION="1.0"
ARCH="all"
WORKDIR="$(pwd)/build"
DEBIAN_DIR="$WORKDIR/DEBIAN"
USR_BIN="$WORKDIR/usr/bin"
ICON_BASE_DIR="$WORKDIR/usr/share/icons/hicolor"
DESKTOP_DIR="$WORKDIR/usr/share/applications"

# Clean up any previous build
rm -rf "$WORKDIR"
mkdir -p "$DEBIAN_DIR" "$USR_BIN" "$DESKTOP_DIR"

# 1. Copy the main script and make it executable
cp Garnicia.py "$USR_BIN/$PKG_NAME"
chmod 755 "$USR_BIN/$PKG_NAME"

# 2. Process icon: trim whitespace and resize to multiple standard sizes
ICON_SIZES=(16 24 32 48 64 128 256 512)
for size in "${ICON_SIZES[@]}"; do
    TARGET_DIR="$ICON_BASE_DIR/${size}x${size}/apps"
    mkdir -p "$TARGET_DIR"
    convert icon.png -trim +repage -resize "${size}x${size}>" \
        "$TARGET_DIR/${PKG_NAME}.png"
done

# 3. Create DEBIAN/control
cat > "$DEBIAN_DIR/control" <<EOF
Package: $PKG_NAME
Version: $PKG_VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: Arthur Dubeux <atdubeux@proton.me>
Depends: python3, python3-gi, gir1.2-gtk-3.0
Description: Garnicia - a GTK3-based journaling application
 A simple note-taking and journaling app using GTK+ 3 and SQLite.
EOF

# 4. Create DEBIAN/copyright
cat > "$DEBIAN_DIR/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Garnicia
Source: local

Files: *
Copyright: 2025 Arthur Dubeux
License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction...
EOF

# 5. Create a simple DEBIAN/rules to satisfy dpkg-deb
cat > "$DEBIAN_DIR/rules" <<'EOF'
#!/usr/bin/make -f
%:
	dh $@
EOF
chmod 755 "$DEBIAN_DIR/rules"

# 6. Install desktop entry
cat > "$DESKTOP_DIR/$PKG_NAME.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Garnicia
Exec=/usr/bin/$PKG_NAME
Icon=$PKG_NAME
Terminal=false
Categories=Utility;Office;
EOF

# 7. Build the .deb package
dpkg-deb --build "$WORKDIR" "${PKG_NAME}_${PKG_VERSION}_${ARCH}.deb"

echo "Built ${PKG_NAME}_${PKG_VERSION}_${ARCH}.deb"

