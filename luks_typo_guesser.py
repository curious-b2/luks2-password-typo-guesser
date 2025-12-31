#!/usr/bin/env python3
"""
LUKS Password Typo Guesser

Attempts to unlock a LUKS2 partition by generating password variations
based on common typing mistakes, configurable by keyboard layout.
"""

import argparse
import subprocess
import sys
from typing import List, Set, Dict, Optional
from itertools import product


class KeyboardLayout:
    """Defines keyboard layout and adjacent key relationships."""
    
    def __init__(self, name: str, adjacent_map: Dict[str, List[str]]):
        """
        Initialize keyboard layout.
        
        Args:
            name: Layout name (e.g., 'QWERTY', 'QWERTZ', 'AZERTY')
            adjacent_map: Dictionary mapping each key to list of adjacent keys
        """
        self.name = name
        self.adjacent_map = adjacent_map
    
    def get_adjacent_keys(self, key: str) -> List[str]:
        """Get keys adjacent to the given key."""
        return self.adjacent_map.get(key.lower(), [])
    
    def get_case_variations(self, key: str) -> List[str]:
        """Get case variations of a key."""
        if key.isalpha():
            return [key.lower(), key.upper()]
        return [key]


class TypoGenerator:
    """Generates password variations based on common typos."""
    
    def __init__(self, keyboard_layout: KeyboardLayout):
        self.layout = keyboard_layout
    
    def generate_typos(self, password: str, max_typos: int = 2) -> Set[str]:
        """
        Generate typo variations of a password.
        
        Args:
            password: Base password to generate typos from
            max_typos: Maximum number of typos to introduce (default: 2)
        
        Returns:
            Set of password variations
        """
        variations: Set[str] = {password}  # Include original
        
        # Single typo variations
        variations.update(self._single_typo_variations(password))
        
        # Multiple typo variations (if max_typos > 1)
        if max_typos > 1:
            for _ in range(max_typos - 1):
                new_variations = set()
                for variant in variations:
                    new_variations.update(self._single_typo_variations(variant))
                variations.update(new_variations)
        
        return variations
    
    def _single_typo_variations(self, password: str) -> Set[str]:
        """Generate variations with a single typo."""
        variations: Set[str] = set()
        
        for i, char in enumerate(password):
            # Adjacent key typos (horizontal/vertical)
            adjacent = self.layout.get_adjacent_keys(char)
            for adj_key in adjacent:
                variant = password[:i] + adj_key + password[i+1:]
                variations.add(variant)
            
            # Case variations
            if char.isalpha():
                if char.islower():
                    variant = password[:i] + char.upper() + password[i+1:]
                else:
                    variant = password[:i] + char.lower() + password[i+1:]
                variations.add(variant)
            
            # Missing character (deletion)
            if len(password) > 1:
                variant = password[:i] + password[i+1:]
                variations.add(variant)
            
            # Duplicate character
            variant = password[:i] + char + char + password[i+1:]
            variations.add(variant)
            
            # Transposition with next character
            if i < len(password) - 1:
                variant = (
                    password[:i] + 
                    password[i+1] + 
                    password[i] + 
                    password[i+2:]
                )
                variations.add(variant)
        
        # Insert adjacent key at each position
        for i in range(len(password) + 1):
            if i > 0:
                prev_char = password[i-1]
                adjacent = self.layout.get_adjacent_keys(prev_char)
                for adj_key in adjacent:
                    variant = password[:i] + adj_key + password[i:]
                    variations.add(variant)
        
        return variations


class LUKSUnlocker:
    """Attempts to unlock LUKS partitions with password variations."""
    
    def __init__(self, device_path: str, slot: int = 0, verbose: bool = False):
        """
        Initialize LUKS unlocker.
        
        Args:
            device_path: Path to LUKS device (e.g., '/dev/sda1')
            slot: Key slot to test (default: 0)
            verbose: Enable verbose output
        """
        self.device_path = device_path
        self.slot = slot
        self.verbose = verbose
    
    def test_password(self, password: str) -> bool:
        """
        Test if a password unlocks the LUKS partition.
        
        Args:
            password: Password to test
        
        Returns:
            True if password is correct, False otherwise
        """
        # Use a unique temporary mapping name based on password hash
        test_mapping = f'luks_test_{abs(hash(password)) % 100000}'
        
        try:
            # Try to open the LUKS device with this password
            cmd = [
                'cryptsetup',
                '--key-slot', str(self.slot),
                'luksOpen',
                self.device_path,
                test_mapping
            ]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=password + '\n', timeout=10)
            
            if process.returncode == 0:
                # Password worked! Close the test mapping immediately
                try:
                    subprocess.run(
                        ['cryptsetup', 'luksClose', test_mapping],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5
                    )
                except Exception:
                    pass  # Ignore errors closing, we got what we needed
                return True
            
            return False
            
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            # Try to close mapping in case it was partially opened
            try:
                subprocess.run(
                    ['cryptsetup', 'luksClose', test_mapping],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=2
                )
            except Exception:
                pass
            return False
        except Exception as e:
            if self.verbose:
                print(f"Error testing password: {e}", file=sys.stderr)
            return False
    
    def try_passwords(self, passwords: List[str]) -> Optional[str]:
        """
        Try a list of passwords and return the first one that works.
        
        Args:
            passwords: List of passwords to try
        
        Returns:
            The correct password if found, None otherwise
        """
        total = len(passwords)
        for i, password in enumerate(passwords, 1):
            if self.verbose:
                print(f"Trying {i}/{total}: {'*' * len(password)}", end='\r', flush=True)
            
            if self.test_password(password):
                if self.verbose:
                    print(f"\n✓ Found correct password at attempt {i}/{total}")
                return password
        
        if self.verbose:
            print(f"\n✗ Tried {total} passwords, none worked")
        return None


# Predefined keyboard layouts
KEYBOARD_LAYOUTS = {
    'QWERTY': KeyboardLayout('QWERTY', {
        'q': ['w', 'a'], 'w': ['q', 'e', 'a', 's'], 'e': ['w', 'r', 's', 'd'],
        'r': ['e', 't', 'd', 'f'], 't': ['r', 'y', 'f', 'g'], 'y': ['t', 'u', 'g', 'h'],
        'u': ['y', 'i', 'h', 'j'], 'i': ['u', 'o', 'j', 'k'], 'o': ['i', 'p', 'k', 'l'],
        'p': ['o', 'l'],
        'a': ['q', 'w', 's', 'z'], 's': ['a', 'w', 'e', 'd', 'x', 'z'],
        'd': ['s', 'e', 'r', 'f', 'c', 'x'], 'f': ['d', 'r', 't', 'g', 'v', 'c'],
        'g': ['f', 't', 'y', 'h', 'b', 'v'], 'h': ['g', 'y', 'u', 'j', 'n', 'b'],
        'j': ['h', 'u', 'i', 'k', 'm', 'n'], 'k': ['j', 'i', 'o', 'l', 'm'],
        'l': ['k', 'o', 'p'],
        'z': ['a', 's', 'x'], 'x': ['z', 's', 'd', 'c'], 'c': ['x', 'd', 'f', 'v'],
        'v': ['c', 'f', 'g', 'b'], 'b': ['v', 'g', 'h', 'n'], 'n': ['b', 'h', 'j', 'm'],
        'm': ['n', 'j', 'k'],
        '1': ['2', 'q'], '2': ['1', '3', 'q', 'w'], '3': ['2', '4', 'w', 'e'],
        '4': ['3', '5', 'e', 'r'], '5': ['4', '6', 'r', 't'], '6': ['5', '7', 't', 'y'],
        '7': ['6', '8', 'y', 'u'], '8': ['7', '9', 'u', 'i'], '9': ['8', '0', 'i', 'o'],
        '0': ['9', 'o', 'p'],
    }),
    
    'QWERTZ': KeyboardLayout('QWERTZ', {
        'q': ['w', 'a'], 'w': ['q', 'e', 'a', 's'], 'e': ['w', 'r', 's', 'd'],
        'r': ['e', 't', 'd', 'f'], 't': ['r', 'z', 'f', 'g'], 'z': ['t', 'u', 'g', 'h'],
        'u': ['z', 'i', 'h', 'j'], 'i': ['u', 'o', 'j', 'k'], 'o': ['i', 'p', 'k', 'l'],
        'p': ['o', 'l'],
        'a': ['q', 'w', 's', 'y'], 's': ['a', 'w', 'e', 'd', 'x', 'y'],
        'd': ['s', 'e', 'r', 'f', 'c', 'x'], 'f': ['d', 'r', 't', 'g', 'v', 'c'],
        'g': ['f', 't', 'z', 'h', 'b', 'v'], 'h': ['g', 'z', 'u', 'j', 'n', 'b'],
        'j': ['h', 'u', 'i', 'k', 'm', 'n'], 'k': ['j', 'i', 'o', 'l', 'm'],
        'l': ['k', 'o', 'p'],
        'y': ['a', 's', 'x'], 'x': ['y', 's', 'd', 'c'], 'c': ['x', 'd', 'f', 'v'],
        'v': ['c', 'f', 'g', 'b'], 'b': ['v', 'g', 'h', 'n'], 'n': ['b', 'h', 'j', 'm'],
        'm': ['n', 'j', 'k'],
        '1': ['2', 'q'], '2': ['1', '3', 'q', 'w'], '3': ['2', '4', 'w', 'e'],
        '4': ['3', '5', 'e', 'r'], '5': ['4', '6', 'r', 't'], '6': ['5', '7', 't', 'z'],
        '7': ['6', '8', 'z', 'u'], '8': ['7', '9', 'u', 'i'], '9': ['8', '0', 'i', 'o'],
        '0': ['9', 'o', 'p'],
    }),
    
    'AZERTY': KeyboardLayout('AZERTY', {
        'a': ['z', 'e', 'q'], 'z': ['a', 'e', 'r', 's'], 'e': ['z', 'a', 'r', 'd'],
        'r': ['e', 't', 'd', 'f'], 't': ['r', 'y', 'f', 'g'], 'y': ['t', 'u', 'g', 'h'],
        'u': ['y', 'i', 'h', 'j'], 'i': ['u', 'o', 'j', 'k'], 'o': ['i', 'p', 'k', 'l'],
        'p': ['o', 'm'],
        'q': ['a', 's', 'w'], 's': ['q', 'a', 'z', 'e', 'd', 'w'],
        'd': ['s', 'e', 'r', 'f', 'c', 'x'], 'f': ['d', 'r', 't', 'g', 'v', 'c'],
        'g': ['f', 't', 'y', 'h', 'b', 'v'], 'h': ['g', 'y', 'u', 'j', 'n', 'b'],
        'j': ['h', 'u', 'i', 'k', 'm', 'n'], 'k': ['j', 'i', 'o', 'l', 'm'],
        'l': ['k', 'o', 'p', 'm'], 'm': ['l', 'p'],
        'w': ['q', 's', 'x'], 'x': ['w', 's', 'd', 'c'], 'c': ['x', 'd', 'f', 'v'],
        'v': ['c', 'f', 'g', 'b'], 'b': ['v', 'g', 'h', 'n'], 'n': ['b', 'h', 'j', 'm'],
        '1': ['2', '&'], '2': ['1', '3', 'é', '&'], '3': ['2', '4', 'é', '"'],
        '4': ['3', '5', '"', "'"], '5': ['4', '6', "'", '('], '6': ['5', '7', '(', '-'],
        '7': ['6', '8', '-', 'è'], '8': ['7', '9', 'è', '_'], '9': ['8', '0', '_', 'ç'],
        '0': ['9', 'à', 'ç'],
    }),
}


def main():
    parser = argparse.ArgumentParser(
        description='Attempt to unlock LUKS2 partition by trying password variations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /dev/sda1 "MyPassword123"
  %(prog)s /dev/nvme0n1p2 "SecretPass" --layout QWERTZ --max-typos 3
  %(prog)s /dev/sdb1 "password" --slot 1 --verbose
        """
    )
    
    parser.add_argument('device', help='LUKS device path (e.g., /dev/sda1)')
    parser.add_argument('base_password', help='The password you think it should be')
    parser.add_argument(
        '--layout',
        choices=list(KEYBOARD_LAYOUTS.keys()),
        default='QWERTY',
        help='Keyboard layout (default: QWERTY)'
    )
    parser.add_argument(
        '--max-typos',
        type=int,
        default=2,
        help='Maximum number of typos to consider (default: 2)'
    )
    parser.add_argument(
        '--slot',
        type=int,
        default=0,
        help='LUKS key slot to test (default: 0)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Get keyboard layout
    layout = KEYBOARD_LAYOUTS[args.layout]
    
    if args.verbose:
        print(f"Using {layout.name} keyboard layout")
        print(f"Base password: {args.base_password}")
        print(f"Generating variations with up to {args.max_typos} typo(s)...")
    
    # Generate typo variations
    generator = TypoGenerator(layout)
    variations = generator.generate_typos(args.base_password, args.max_typos)
    
    if args.verbose:
        print(f"Generated {len(variations)} password variations")
        print(f"Testing against {args.device} (slot {args.slot})...")
        print()
    
    # Try to unlock
    unlocker = LUKSUnlocker(args.device, args.slot, args.verbose)
    correct_password = unlocker.try_passwords(list(variations))
    
    if correct_password:
        print(f"\n✓ SUCCESS! Correct password found: {correct_password}")
        return 0
    else:
        print(f"\n✗ FAILED: None of the {len(variations)} variations worked")
        print("\nSuggestions:")
        print("  - Try increasing --max-typos")
        print("  - Verify the keyboard layout with --layout")
        print("  - Check if the correct key slot is specified with --slot")
        return 1


if __name__ == '__main__':
    sys.exit(main())

