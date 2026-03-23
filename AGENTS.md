# AGENTS.md

We operate inside this HarfBuzz open source project directory to develop an avar2 test font that tests kerning and multiple axis mapping through Avar2. 

# AVAR2 knowledge

AVAR1 font specs are found here: https://learn.microsoft.com/en-us/typography/opentype/spec/avar
From file:///usr/local/google/home/drott/dev/notosanssymbol/WG03_otf-improvements.pdf inform yourself about avar2 structure.
Especially section: 6.4.2. Duplication of axis values for non-linear interpolation is important and the concept of what we want to use to control the workings of the font.

## Verification

Using hb-shape <font-file> --unicodes U+.... and specifying variation parameters, the behavior of the test font can be verified.
hb-shape is available from build/util/hb-shape.


## Design idea of the font

The test font is supposed to have two implementation axes, XKRN and YKRN, which together describe a counterclockwise 90 degree path from the two glyphs being horizontally next to each other, to ending in the right glyph being on top of the first glyph. 

XKRN and YKRN should be set to hidden in the fvar variations table.

An exposed axis CKRN should be created that controls the counterclockwise rotation, by driving the hidden axis XKRN and YKRN through avar2.

The test codepoints are U+2316 (CROSS) and U+0020 (SPACE).

## Final font production 

For getting standard tables like OS/2, hvar etc. right, at the end of font generation with @create_avar2_test_font.py, run the font through fontTools.ttx to dump it to ttx, then re-encode it.


## fontTools.ttx usage instructions

When generating output files, use an -o parameter to avoid creating too many temporary noisy files.
