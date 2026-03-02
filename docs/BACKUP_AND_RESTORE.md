# Backup and Restore Guide

SSHive provides comprehensive backup and restore functionality to protect your SSH connection configurations. Automatic backups are created whenever you make changes, and you can export connections to files or import from backups.

## Overview

Backup and restore options are accessible from the **Options** menu → **Backup and Restore** submenu, and settings are configurable in **Options** → **Settings**.

### Storage Location

- **Linux/macOS:** `~/.config/sshive/`
- **Windows:** `%APPDATA%\sshive\`

Your main connections are stored in `connections.json` in this directory.

## Features

### 1. Automatic Backups

**Default Behavior:** Every time you add, edit, or delete a connection, SSHive automatically creates a timestamped backup in your config folder.

#### What happens:
- Saves a copy of your connections as `connections-backup-YYYYMMDD-HHMMSS.json`
- Automatically rotates and deletes old backups to prevent disk space issues
- Number of backups to keep is configurable in Settings (default: 10)

#### Example:
- `connections-backup-20260302-143022.json`
- `connections-backup-20260302-120515.json`
- `connections-backup-20260301-180930.json`

#### Configuration:
Go to **Options** → **Settings** → "Automatic backups to keep:" to set how many backups to retain (1-50, default 10).

### 2. Export Connections

**Menu:** Options → Backup and Restore → Export Connections

Saves your connections to a location of your choice.

#### What it does:
- Opens a file browser to select export destination
- Saves connections as standard JSON format
- Portable - can be moved to other machines or stored in cloud storage

#### Filename suggestions:
- `connections-backup-2026-03-02.json`
- `sshive-prod-servers.json`
- `sshive-staging-servers.json`

#### Use cases:
- Create portable backups stored in cloud storage (Dropbox, OneDrive, Google Drive)
- Share connection templates with team members
- Archive specific configurations by date or project
- Version control your connection list (Git)

### 3. Import Connections

**Menu:** Options → Backup and Restore → Import Connections

Restore connections from an exported backup file.

#### What it does:
- Opens a file browser to select import source
- Provides two import modes:
  - **Merge**: Combines imported connections with existing ones
  - **Replace**: Overwrites all connections with imported ones

#### Import Modes:

**Merge Mode**
- Combines imported connections with your current connections
- Duplicate connections (same ID) are skipped - existing connections are kept
- Useful for adding new connections from a backup without losing current ones
- Safe option when in doubt

**Replace Mode**
- Completely replaces all your current connections with the imported set
- Existing connections are removed
- Recent connection history is NOT cleared
- Use when restoring a full backup

#### Use cases:
- Restore from a previous backup after accidental changes
- Import connections exported from another machine
- Merge team connection templates into your setup
- Restore from version control after local changes

### 4. Open Config Folder

**Menu:** Options → Backup and Restore → Open Config Folder

Opens your configuration folder in the system file manager.

#### Use cases:
- Manual file management
- Browse all backup files
- Copy files manually to external storage
- Verify backup creation
- Direct access for advanced users

## Workflow Examples

### Daily Protection Workflow

1. SSHive automatically creates timestamped backups of your connections whenever you make changes
2. Make changes to your connections normally
3. If something goes wrong: **Open Config Folder** → find your recent backup file and rename it to `connections.json`
4. Restart SSHive

### Cloud Backup Workflow

1. **Export Connections** to your cloud storage folder (e.g., `~/Dropbox/sshive-backup.json`)
2. Your cloud service automatically syncs it
3. To restore: **Import Connections** from the cloud location

### Team Sharing Workflow

1. Team admin exports commonly used connections: **Export Connections**
2. Shares the file with team members
3. Each team member: **Import Connections** (Merge mode) to add shared servers
4. Team members can add their personal servers without losing shared ones

### Migration to New Machine

1. On old machine: **Export Connections** to portable location
2. Transfer the file to new machine (USB, email, cloud storage, etc.)
3. On new machine: **Import Connections** (Replace mode)
4. All connections are now available

### Version Control Workflow

```bash
# Export connections
cp ~/.config/sshive/connections.json ~/my-project/sshive-connections.json

# Commit to git
git add sshive-connections.json
git commit -m "Update SSH connections"

# Later: restore from git
cp ~/my-project/sshive-connections.json ~/.config/sshive/connections.json
# Restart SSHive
```

## Backup Rotation

The automatic backup feature includes intelligent log rotation:

- **Maximum backups kept:** Configurable in Settings (default: 10)
- **Old backups deleted:** Automatically when limit is exceeded
- **Order maintained:** Oldest backups are removed first
- **When it happens:** Every time you modify connections (add, edit, or delete)

This prevents your config folder from filling up with backup files over time while keeping recent recovery points available.

### Configure Backup Retention

1. Open **Options** → **Settings**
2. Find "Automatic backups to keep:" field
3. Adjust the value (1-50 backups)
4. Click **Save**

The new setting takes effect immediately for future backups.

## Best Practices

1. **Regular Exports**: Export your connections to cloud storage at least monthly
2. **Before Major Changes**: Create a backup before adding many new connections
3. **Version Control**: Keep your connections.json in git for important configurations
4. **Test Imports**: Test import functionality with a backup on a non-production machine first
5. **Merge by Default**: Use Merge mode when importing unless you specifically want to replace everything
6. **File Naming**: Use descriptive names: `sshive-prod-backup-2026-03-02.json`

## Troubleshooting

### Import Failed

**Symptom:** "Failed to import connections"

**Solutions:**
- Verify the file is a valid SSHive backup (JSON format)
- Check file permissions
- Ensure the file hasn't been corrupted
- Try exporting a fresh backup and re-importing

### Can't Open Config Folder

**Symptom:** "Could not open folder"

**Solutions:**
- Try using **Open Config Folder** to navigate manually
- Check folder exists: `~/.config/sshive/` or `%APPDATA%\sshive\`
- Verify file manager is installed and associated with folders
- Check folder permissions

### Duplicate Connections After Merge

**Symptom:** Same connections appear twice

**Cause:** Import mode was set to Replace, or IDs were different

**Solution:**
- Use Merge mode to automatically skip duplicates
- Manually delete duplicate entries in the UI

## File Format

Backup files are standard JSON. Example structure:

```json
{
  "version": "1.0",
  "connections": [
    {
      "id": "unique-id-123",
      "name": "Production Server",
      "host": "prod.example.com",
      "user": "admin",
      "port": 22,
      "key": null,
      "group": "Production",
      "tunnels": []
    }
  ],
  "recent_connections": []
}
```

You can safely view and edit these files manually if needed, but it's recommended to use the UI.

## Security Considerations

- Backup files contain your SSH connection details (hostnames, usernames, but NOT passwords or keys)
- Store backups securely, especially if they contain production server information
- Use encrypted cloud storage for sensitive backups
- Don't commit backups with sensitive data to public repositories
- Keep SSH keys separate and backed up independently

## See Also

- [Installation Guide](../README.md)
- [Usage Guide](../README.md#usage)
