# LUKS Password Typo Guesser

A Python script to help recover LUKS2 partition passwords by generating and testing password variations based on common typing mistakes. The typo generation is configurable based on keyboard layout.

## Features

- Generates password variations based on common typos:
  - Adjacent key mistakes (horizontal/vertical)
  - Case variations
  - Missing characters
  - Duplicate characters
  - Transposed characters
  - Inserted characters
- Supports multiple keyboard layouts:
  - QWERTY (default)
  - QWERTZ
  - AZERTY
- Configurable maximum number of typos
- Tests against specific LUKS key slots

## Requirements

- Python 3.6+
- `cryptsetup` command-line tool (standard on Linux systems)
- Root/sudo access to test LUKS devices

## Usage

Basic usage:
```bash
sudo python3 luks_typo_guesser.py /dev/sda1 "MyPassword123"
```

With options:
```bash
sudo python3 luks_typo_guesser.py /dev/nvme0n1p2 "SecretPass" \
    --layout QWERTZ \
    --max-typos 3 \
    --slot 1 \
    --verbose
```

### Arguments

- `device`: Path to the LUKS device (e.g., `/dev/sda1`, `/dev/nvme0n1p2`)
- `base_password`: The password you think it should be
- `--layout`: Keyboard layout (QWERTY, QWERTZ, AZERTY) - default: QWERTY
- `--max-typos`: Maximum number of typos to consider - default: 2
- `--slot`: LUKS key slot to test - default: 0
- `--verbose, -v`: Enable verbose output showing progress

## How It Works

1. Takes the base password you think is correct
2. Generates variations by introducing common typing mistakes:
   - Replacing characters with adjacent keys on the keyboard
   - Changing case
   - Removing characters
   - Duplicating characters
   - Transposing adjacent characters
   - Inserting adjacent keys
3. Tests each variation against the LUKS partition using `cryptsetup`
4. Reports the correct password if found

## Example

If you think the password is "Password123" but typed it on a QWERTY keyboard, the script will try variations like:
- "Pqssword123" (adjacent key)
- "password123" (case change)
- "Passwod123" (missing character)
- "Passsword123" (duplicate)
- "Pasword123" (transposition)
- And many more...

## Security Note

This script requires root/sudo access to test LUKS devices. Use responsibly and only on devices you own or have explicit permission to access.

## Limitations

- The number of variations grows exponentially with `--max-typos`
- Testing many passwords can be slow
- Only works with LUKS2 partitions (though may work with LUKS1)
- Requires `cryptsetup` to be installed

## Adding Custom Keyboard Layouts

You can extend the script by adding new layouts to the `KEYBOARD_LAYOUTS` dictionary. Each layout maps keys to their adjacent keys (horizontally and vertically).

# luks2-password-typo-guesser
# luks2-password-typo-guesser
# luks2-password-typo-guesser -- LLM-generated first pass
