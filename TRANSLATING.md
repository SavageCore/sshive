# Translating SSHive

Thank you for helping translate SSHive! This guide explains how to add or update translations.

## Quick Start: Use Weblate

**The easiest way to translate SSHive is on [Weblate](https://hosted.weblate.org/projects/sshive/).** Simply select your language and start translating — no repo cloning, no manual compilation needed.

## Overview

SSHive uses the Qt Linguist translation system (`.ts` / `.qm` files). The source language is **English** and translation files live in `sshive/i18n/`.

For general developer setup and workflow, please refer to the [Contributing Guide](CONTRIBUTING.md).

| File type | Purpose                                  |
| --------- | ---------------------------------------- |
| `.ts`     | XML source files that translators edit   |
| `.qm`    | Compiled binary files loaded at runtime  |

## For Translators: Use Weblate

Visit [Weblate](https://hosted.weblate.org/projects/sshive/) and sign up. Select your language or request a new one, then start translating. That's it — your translations sync automatically.

## For Developers: Manual Workflow

If you need to update source strings or work with translations locally, use the manual process below.

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- PySide6 (`pyside6-lupdate` and `pyside6-lrelease` CLI tools)

Install dependencies:

```bash
make dev
```

### 1. Update Source Strings

Extract all translatable strings from the source code into the base `.ts` file:

```bash
pyside6-lupdate sshive/ui/*.py -ts sshive/i18n/en.ts
```

### 2. Add a New Language

Copy the English source file and rename it with the appropriate locale code:

```bash
cp sshive/i18n/en.ts sshive/i18n/<lang>.ts
```

For example, for French:

```bash
cp sshive/i18n/en.ts sshive/i18n/fr.ts
```

Common locale codes: `de` (German), `fr` (French), `es` (Spanish), `ja` (Japanese), `zh` (Chinese), `pt_BR` (Brazilian Portuguese).

### 3. Translate Strings

Open the `.ts` file in **Qt Linguist** (recommended) or any text editor.

#### Using Qt Linguist (GUI)

```bash
pyside6-linguist sshive/i18n/<lang>.ts
```

Qt Linguist provides a dedicated translation interface with context, source text, and a field for your translation.

#### Using a Text Editor

Each translatable string looks like this in the `.ts` file:

```xml
<message>
    <location filename="../ui/main_window.py" line="123"/>
    <source>Add Connection</source>
    <translation type="unfinished"></translation>
</message>
```

To translate, replace the empty `<translation>` tag and remove `type="unfinished"`:

```xml
<message>
    <location filename="../ui/main_window.py" line="123"/>
    <source>Add Connection</source>
    <translation>Verbinding toevoegen</translation>
</message>
```

### 4. Compile Translations

Compile the `.ts` file into a `.qm` binary:

```bash
pyside6-lrelease sshive/i18n/<lang>.ts -qm sshive/i18n/<lang>.qm
```

### 5. Test Your Translation

Run SSHive and select your language in **Settings → Language**:

```bash
make run
```

> **Note:** A restart is required after changing the language.

### 6. Register the Language (Optional)

To show a human-readable name in the settings dropdown, add your locale code to the `_LANGUAGE_NAMES` dictionary in `sshive/ui/settings_dialog.py`:

```python
_LANGUAGE_NAMES: dict[str, str] = {
    "system": "System Default",
    "en": "English",
    "fr": "French (Français)",  # ← add your language here
}
```

If you skip this step, SSHive will fall back to Qt's built-in locale name, which usually works fine.

## Translation Tips

- **Don't translate** brand names (`SSHive`, `PySide6`, `SSH`) or keyboard shortcuts (`Ctrl+I`).
- **Keep HTML tags** intact (e.g. `<b>SSHive</b>` should stay as `<b>SSHive</b>`).
- **Placeholders** like `{}` or `{0}` must remain in the translation — they are filled in at runtime.
- **Ampersands** (`&`) in button/menu labels mark keyboard accelerators (e.g. `&File` underlines the F). Try to keep accelerators unique within each dialog.

## Submitting Translations

**Via Weblate (recommended):** Translations submitted on Weblate are automatically synced to the repository. No manual PR needed.

**Manually:** If you prefer to contribute outside Weblate:
1. Fork the repository
2. Create a branch: `git checkout -b translate/<lang>`
3. Add both the `.ts` and `.qm` files
4. Open a Pull Request

## File Structure

```
sshive/i18n/
├── en.ts       # English source (base)
├── en.qm       # English compiled
├── fr.ts       # French translation (example)
└── fr.qm       # French compiled (example)
```

## Questions?

Open an issue on GitHub if you need help or have questions about translating.
