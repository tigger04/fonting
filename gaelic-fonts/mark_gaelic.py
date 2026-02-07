#!/usr/bin/env python3
# ABOUTME: Marks OTF/WOFF2 font files with Irish (Gaelic) language metadata.
# ABOUTME: Modifies name table, OS/2 unicode ranges, and GSUB language tags.

"""Mark font files with Irish (Gaelic) language metadata.

Usage:
    python mark_gaelic.py [directory]

If no directory is given, processes fonts in the current directory.
Modifies each qualifying font file in-place to add:
  - Irish language name records (langID 0x083C)
  - OS/2 Latin Extended Additional bit (for dotted consonants)
  - IRI language tag in GSUB latn script
"""

import os
import sys

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables

# Irish (Ireland) language ID for Windows platform
IRISH_LANG_ID = 0x083C  # 2108 decimal

# Windows platform constants
PLATFORM_WINDOWS = 3
ENCODING_UNICODE_BMP = 1
LANG_ENGLISH_US = 1033

# OS/2 bit 29 = Latin Extended Additional (covers ḃ, ċ, ḋ, ḟ, ġ, ṁ, ṗ, ṡ, ṫ)
BIT_29_MASK = 1 << 29

# OpenType language system tag for Irish
IRI_TAG = "IRI "

# Name IDs to duplicate into Irish
# 1=Family, 2=Subfamily, 4=Full name, 5=Version, 6=PostScript name
NAME_IDS_TO_COPY = {1, 2, 4, 5, 6}

# Filename prefixes to exclude
EXCLUDED_PREFIXES = ("SF-Pro",)

# Valid font extensions
FONT_EXTENSIONS = (".otf", ".woff2")


def should_process_font(filename):
    """Determine whether a font file should be processed.

    Args:
        filename: The font filename (not full path).

    Returns:
        True if the font should be marked as Gaelic.
    """
    _, ext = os.path.splitext(filename)
    if ext.lower() not in FONT_EXTENSIONS:
        return False

    for prefix in EXCLUDED_PREFIXES:
        if filename.startswith(prefix):
            return False

    return True


def _add_irish_name_records(font):
    """Add Irish language name records by copying English ones.

    Copies relevant Windows-platform English name records to Irish langID.
    Skips records that already exist to ensure idempotency.
    """
    name_table = font["name"]

    # Find existing Irish records to avoid duplication
    existing_irish = {
        (rec.nameID, rec.platformID, rec.platEncID)
        for rec in name_table.names
        if rec.langID == IRISH_LANG_ID
    }

    # Find English Windows records to copy
    english_records = [
        rec
        for rec in name_table.names
        if rec.platformID == PLATFORM_WINDOWS
        and rec.platEncID == ENCODING_UNICODE_BMP
        and rec.langID == LANG_ENGLISH_US
        and rec.nameID in NAME_IDS_TO_COPY
    ]

    for rec in english_records:
        key = (rec.nameID, rec.platformID, rec.platEncID)
        if key not in existing_irish:
            name_table.setName(
                rec.toUnicode(),
                rec.nameID,
                PLATFORM_WINDOWS,
                ENCODING_UNICODE_BMP,
                IRISH_LANG_ID,
            )


def _set_os2_latin_extended_additional(font):
    """Set OS/2 ulUnicodeRange1 bit 29 (Latin Extended Additional).

    This indicates support for characters like ḃ, ċ, ḋ, ḟ, ġ, ṁ, ṗ, ṡ, ṫ
    used in traditional Irish orthography with séimhiú (lenition dots).
    """
    if "OS/2" in font:
        font["OS/2"].ulUnicodeRange1 |= BIT_29_MASK


def _add_gsub_iri_language(font):
    """Add IRI (Irish) language system tag to the GSUB latn script.

    Creates a LangSysRecord pointing to the default LangSys, ensuring
    Irish text gets the same OpenType feature lookups as the default.
    """
    if "GSUB" not in font:
        return

    gsub = font["GSUB"].table
    if not gsub.ScriptList:
        return

    for script_rec in gsub.ScriptList.ScriptRecord:
        if script_rec.ScriptTag != "latn":
            continue

        script = script_rec.Script
        if script.LangSysRecord is None:
            script.LangSysRecord = []

        # Check if IRI already exists
        existing_tags = [lr.LangSysTag for lr in script.LangSysRecord]
        if IRI_TAG in existing_tags:
            return

        # Create IRI LangSys that mirrors the default
        iri_langsys = otTables.LangSys()
        iri_langsys.LookupOrder = None

        if script.DefaultLangSys:
            iri_langsys.ReqFeatureIndex = script.DefaultLangSys.ReqFeatureIndex
            iri_langsys.FeatureIndex = list(script.DefaultLangSys.FeatureIndex or [])
            iri_langsys.FeatureCount = len(iri_langsys.FeatureIndex)
        else:
            iri_langsys.ReqFeatureIndex = 0xFFFF
            iri_langsys.FeatureIndex = []
            iri_langsys.FeatureCount = 0

        lang_record = otTables.LangSysRecord()
        lang_record.LangSysTag = IRI_TAG
        lang_record.LangSys = iri_langsys

        script.LangSysRecord.append(lang_record)
        script.LangSysCount = len(script.LangSysRecord)

        break


def mark_font_gaelic(filepath):
    """Apply all Gaelic metadata modifications to a single font file.

    Args:
        filepath: Path to the OTF or WOFF2 font file to modify.
    """
    font = TTFont(filepath)

    _add_irish_name_records(font)
    _set_os2_latin_extended_additional(font)
    _add_gsub_iri_language(font)

    font.save(filepath)
    font.close()


def process_directory(directory):
    """Process all qualifying font files in a directory.

    Args:
        directory: Path to the directory containing font files.

    Returns:
        List of filenames that were processed.
    """
    processed = []

    for filename in sorted(os.listdir(directory)):
        if not should_process_font(filename):
            continue

        filepath = os.path.join(directory, filename)
        if not os.path.isfile(filepath):
            continue

        print(f"Marking: {filename}")
        mark_font_gaelic(filepath)
        processed.append(filename)

    return processed


def main():
    """Entry point for command-line usage."""
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = os.getcwd()

    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a directory", file=sys.stderr)
        sys.exit(1)

    processed = process_directory(directory)
    print(f"\nDone. Marked {len(processed)} font files as Gaelic.")


if __name__ == "__main__":
    main()
