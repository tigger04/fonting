# ABOUTME: Tests for mark_gaelic.py — verifies Gaelic language metadata is correctly
# ABOUTME: applied to OTF and WOFF2 font files.

import os
import shutil
import tempfile

import pytest
from fontTools.ttLib import TTFont

# Irish language ID for Windows platform (platformID=3, encID=1)
IRISH_LANG_ID = 0x083C  # 2108 decimal

# OpenType language tag for Irish
IRI_TAG = "IRI "

# OS/2 bit 29 mask for Latin Extended Additional
BIT_29_MASK = 1 << 29


@pytest.fixture
def temp_font_dir():
    """Create a temporary directory with copies of test fonts."""
    src_dir = os.path.dirname(os.path.abspath(__file__))
    with tempfile.TemporaryDirectory() as tmpdir:
        # Copy a few representative OTF files
        for fname in ["aonchlo.otf", "richlo.otf", "bungc.otf"]:
            src = os.path.join(src_dir, fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(tmpdir, fname))

        # Copy a WOFF2 file
        for fname in ["richlo.woff2", "bungc.woff2"]:
            src = os.path.join(src_dir, fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(tmpdir, fname))

        # Copy an SF-Pro font (should be excluded)
        sf_name = "SF-Pro-Text-Bold.otf"
        src = os.path.join(src_dir, sf_name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(tmpdir, sf_name))

        yield tmpdir


class TestMarkGaelic:
    """Tests for the mark_gaelic module."""

    def test_name_table_gets_irish_records(self, temp_font_dir):
        """After marking, font should have name records with Irish langID."""
        from mark_gaelic import mark_font_gaelic

        fpath = os.path.join(temp_font_dir, "aonchlo.otf")
        mark_font_gaelic(fpath)

        font = TTFont(fpath)
        irish_records = [
            rec
            for rec in font["name"].names
            if rec.platformID == 3
            and rec.platEncID == 1
            and rec.langID == IRISH_LANG_ID
        ]
        font.close()

        # Should have at least the core name records duplicated in Irish
        assert len(irish_records) > 0, "No Irish language name records found"

        # Should have nameID 1 (family name) in Irish
        irish_name_ids = {rec.nameID for rec in irish_records}
        assert 1 in irish_name_ids, "Missing Irish family name record (nameID=1)"

    def test_existing_english_records_preserved(self, temp_font_dir):
        """Marking should not remove existing English name records."""
        from mark_gaelic import mark_font_gaelic

        fpath = os.path.join(temp_font_dir, "aonchlo.otf")

        # Count English records before
        font_before = TTFont(fpath)
        english_before = [
            rec
            for rec in font_before["name"].names
            if rec.platformID == 3 and rec.langID == 1033
        ]
        count_before = len(english_before)
        font_before.close()

        mark_font_gaelic(fpath)

        # Count English records after
        font_after = TTFont(fpath)
        english_after = [
            rec
            for rec in font_after["name"].names
            if rec.platformID == 3 and rec.langID == 1033
        ]
        font_after.close()

        assert len(english_after) == count_before, "English name records were modified"

    def test_os2_bit29_set(self, temp_font_dir):
        """After marking, OS/2 ulUnicodeRange1 bit 29 should be set."""
        from mark_gaelic import mark_font_gaelic

        # aonchlo does NOT have bit 29 set initially
        fpath = os.path.join(temp_font_dir, "aonchlo.otf")
        mark_font_gaelic(fpath)

        font = TTFont(fpath)
        assert font["OS/2"].ulUnicodeRange1 & BIT_29_MASK, (
            "OS/2 bit 29 (Latin Extended Additional) not set"
        )
        font.close()

    def test_os2_bit29_preserved_when_already_set(self, temp_font_dir):
        """If bit 29 is already set, it should remain set and other bits untouched."""
        from mark_gaelic import mark_font_gaelic

        # bungc already has bit 29 set
        fpath = os.path.join(temp_font_dir, "bungc.otf")

        font_before = TTFont(fpath)
        range_before = font_before["OS/2"].ulUnicodeRange1
        font_before.close()

        mark_font_gaelic(fpath)

        font_after = TTFont(fpath)
        range_after = font_after["OS/2"].ulUnicodeRange1
        font_after.close()

        # Bit 29 still set
        assert range_after & BIT_29_MASK

        # Other bits unchanged (bit 29 was already set, so value should be same)
        assert range_after == range_before, "Other OS/2 unicode range bits were modified"

    def test_gsub_iri_language_added(self, temp_font_dir):
        """After marking, GSUB latn script should include IRI language tag."""
        from mark_gaelic import mark_font_gaelic

        fpath = os.path.join(temp_font_dir, "aonchlo.otf")
        mark_font_gaelic(fpath)

        font = TTFont(fpath)
        gsub = font["GSUB"].table

        latn_script = None
        for script_rec in gsub.ScriptList.ScriptRecord:
            if script_rec.ScriptTag == "latn":
                latn_script = script_rec.Script
                break

        assert latn_script is not None, "No latn script in GSUB"

        lang_tags = [lr.LangSysTag for lr in (latn_script.LangSysRecord or [])]
        assert IRI_TAG in lang_tags, f"IRI language tag not found in GSUB latn. Found: {lang_tags}"

        font.close()

    def test_gsub_iri_not_duplicated(self, temp_font_dir):
        """Running mark twice should not duplicate the IRI language tag."""
        from mark_gaelic import mark_font_gaelic

        fpath = os.path.join(temp_font_dir, "aonchlo.otf")
        mark_font_gaelic(fpath)
        mark_font_gaelic(fpath)

        font = TTFont(fpath)
        gsub = font["GSUB"].table

        for script_rec in gsub.ScriptList.ScriptRecord:
            if script_rec.ScriptTag == "latn":
                lang_tags = [lr.LangSysTag for lr in (script_rec.Script.LangSysRecord or [])]
                iri_count = lang_tags.count(IRI_TAG)
                assert iri_count == 1, f"IRI tag duplicated: found {iri_count} times"
                break

        font.close()

    def test_woff2_handled(self, temp_font_dir):
        """WOFF2 files should be handled correctly."""
        from mark_gaelic import mark_font_gaelic

        fpath = os.path.join(temp_font_dir, "richlo.woff2")
        mark_font_gaelic(fpath)

        font = TTFont(fpath)

        # Check Irish name records
        irish_records = [
            rec
            for rec in font["name"].names
            if rec.platformID == 3 and rec.langID == IRISH_LANG_ID
        ]
        assert len(irish_records) > 0, "No Irish name records in WOFF2 file"

        # Check OS/2 bit 29
        assert font["OS/2"].ulUnicodeRange1 & BIT_29_MASK, (
            "OS/2 bit 29 not set in WOFF2 file"
        )

        font.close()

    def test_sf_pro_excluded(self, temp_font_dir):
        """SF-Pro-Text fonts should be excluded from modification."""
        from mark_gaelic import should_process_font

        assert not should_process_font("SF-Pro-Text-Bold.otf")
        assert not should_process_font("SF-Pro-Text-Medium.otf")

    def test_gaelic_fonts_included(self):
        """Gaelic font filenames should be included for processing."""
        from mark_gaelic import should_process_font

        assert should_process_font("aonchlo.otf")
        assert should_process_font("richlo.woff2")
        assert should_process_font("Lamhchlo.otf")
        assert should_process_font("bungc.otf")

    def test_only_otf_and_woff2_processed(self):
        """Only .otf and .woff2 files should be processed."""
        from mark_gaelic import should_process_font

        assert not should_process_font("Credits.rtf")
        assert not should_process_font("README.md")
        assert not should_process_font("requirements.txt")

    def test_idempotent_name_records(self, temp_font_dir):
        """Running mark twice should not duplicate Irish name records."""
        from mark_gaelic import mark_font_gaelic

        fpath = os.path.join(temp_font_dir, "richlo.otf")
        mark_font_gaelic(fpath)

        font1 = TTFont(fpath)
        count1 = len([
            rec for rec in font1["name"].names
            if rec.platformID == 3 and rec.langID == IRISH_LANG_ID
        ])
        font1.close()

        mark_font_gaelic(fpath)

        font2 = TTFont(fpath)
        count2 = len([
            rec for rec in font2["name"].names
            if rec.platformID == 3 and rec.langID == IRISH_LANG_ID
        ])
        font2.close()

        assert count1 == count2, (
            f"Irish records duplicated on second run: {count1} vs {count2}"
        )
