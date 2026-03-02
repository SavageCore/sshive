# PuTTY/KiTTY Session Import

SSHive supports importing SSH sessions from PuTTY and KiTTY configuration files. This makes it easy to migrate your existing session configurations to SSHive.

## Supported Formats

### PuTTY Registry Export (.reg)
Windows registry export format (exported from PuTTY via Tools → Export Sessions).

Example:
```
Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\Software\SimonTatham\PuTTY\Sessions\My Server]
"HostName"="example.com"
"UserName"="ubuntu"
"PortNumber"=dword:00000016
"PublicKeyFile"="C:\\Users\\john\\.ssh\\id_rsa"
```

### PuTTY Portable INI Format (putty.ini)
INI-format configuration file used by portable PuTTY installations.

Example:
```
[Production Server]
HostName=prod.example.com
UserName=produser
PortNumber=2222
PublicKeyFile=/home/user/.ssh/prod_key

[Staging Server]
HostName=staging.example.com
UserName=staginguser
PortNumber=22
```

### KiTTY Portable INI Format (kitty.ini)
KiTTY uses a compatible INI format to PuTTY for maximum portability.

## How to Import

1. Go to **Settings** → **Backup and Restore** menu
2. Click **Import from PuTTY/KiTTY**
3. Choose import source:
   - **Select Files**: Pick one or more files (`.reg`, `.ini`, `.conf`, or extensionless Linux session files)
   - **Browse Folder**: Select a PuTTY sessions directory (for example `~/.putty/sessions/`)
4. Choose how to apply imports:
   - **Add to Existing**: Keep current entries and append imported sessions
   - **Replace All**: Remove all existing entries and keep only imported sessions
5. If you choose **Replace All**, SSHive shows a confirmation dialog before any data is replaced.

### Config File Locations

The import dialog will automatically search for config files in these locations:

**Linux:**
- PuTTY sessions directory: `~/.putty/sessions/`
- PuTTY base directory: `~/.putty/`
- KiTTY: `~/.config/KiTTY/` directory
- Generic: `~/.config/` directory

**macOS:**
- Similar to Linux, though some installations may use different paths

**Windows:**
- Registry: Use "Export Sessions" from PuTTY to get a `.reg` file
- Portable: Check the installation directory for `putty.ini`

## What Gets Imported

The importer extracts the following information from PuTTY/KiTTY configurations:

- **HostName/hostname** → SSH host/IP address
- **UserName/username** → SSH username (defaults to "root" if not specified)
- **PortNumber/portnumber** → SSH port (defaults to 22)
- **PublicKeyFile/publickeyfile** → SSH private key path (if file exists)

Imported sessions are placed in the "Imported from PuTTY" group.

## Auto-Detection

SSHive automatically detects the format based on content, including extensionless Linux PuTTY session files (`key=value` format).

## Limitations

- Only SSH connection parameters are imported; PuTTY-specific settings (terminal colors, fonts, etc.) are not transferred
- SSH key paths are verified to exist; non-existent paths are silently ignored
- Sessions without a hostname are skipped during import

## Migration Strategy

### From Linux Installed PuTTY

1. PuTTY sessions are typically stored in `~/.putty/sessions/` as one file per session.
2. In SSHive, use **Import from PuTTY/KiTTY**.
3. Choose either:
   - **Browse Folder** and select `~/.putty/sessions/`, or
   - **Select Files** and choose one or more session files from that directory.

### From Linux Portable Installation

1. Locate your `putty.ini` or `kitty.ini` configuration file (usually in the portable app directory)
2. In SSHive, use **Import from PuTTY/KiTTY** and select the `.ini` file
3. Verify that your SSH keys are accessible from your current Linux installation

### From Windows (Using Registry Export)

1. In PuTTY, go to **Tools** → **Export Sessions** to save a `.reg` file
2. Transfer the `.reg` file to your Linux/macOS machine
3. In SSHive, use **Import from PuTTY/KiTTY** and select the `.reg` file

### From Portable Installation (Cross-Platform)

1. Locate your `putty.ini` or `kitty.ini` configuration file
2. In SSHive, use **Import from PuTTY/KiTTY** and select the `.ini` file
3. Verify that your SSH keys are converted to Unix-style paths if you migrated them

## Troubleshooting

### "No valid sessions found in the file"
- Ensure the file is a valid PuTTY or KiTTY configuration
- Check that sessions have at least a hostname defined
- Try exporting the registry again or locating the portable config file
- On Linux, check `~/.putty/sessions/` for installed PuTTY session files

### SSH keys not being imported
- Verify the key file paths are correct and accessible
- On Linux/macOS, key paths need to be Unix-style (e.g., `/home/user/.ssh/id_rsa`)
- If paths use Windows format, update them manually in SSHive after import
- Key files must exist on the current system to be imported

### Finding PuTTY config files on Linux
- Installed PuTTY: `ls -la ~/.putty/` to view all sessions
- KiTTY portable: Check `~/.config/KiTTY/` or the KiTTY installation directory
- Use the file browser to navigate to these directories

### Duplicate sessions after merge
- If you merge and end up with duplicates, use replace mode to reimport cleanly
