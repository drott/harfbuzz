#!/usr/bin/env python3
"""
Create a test font with avar2 variable kerning trace.
Axes:
- CKRN (User visible control axis, 0 to 1)
- XKRN (Hidden axis, horizontal offset)
- YKRN (Hidden axis, vertical offset)

Glyphs:
- space (U+0020)
- cross (U+2316)

Pair (cross, cross) kerning will be driven by CKRN and trace a quarter circle.
"""

import sys
from fontTools.ttLib import TTFont, newTable
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib.tables.otBase import OTTableWriter
from fontTools.ttLib.tables import otTables as ot
from fontTools.varLib.models import VariationModel
from fontTools.varLib.builder import buildVarStore, buildVarRegionList, buildVarData, buildVarIdxMap
import math
import struct

# Constants
WIDTH = 1024
CENTER = 512
THICKNESS = 12

def create_glyph_cross():
    # Vertical bar
    # (506, 0), (518, 0), (518, 1024), (506, 1024)
    # Horizontal bar
    # (0, 506), (1024, 506), (1024, 518), (0, 518)
    
    # Using fontTools.pens to draw
    # But for TrueType (glyf) we can just use setGlyphGVar or similar?
    # No, for FontBuilder we can pass a dict of glyph data (contour list of points)
    # Or use a pen.
    pass

def main():
    # 1. Initialize FontBuilder
    fb = FontBuilder(WIDTH)
    
    # 2. Setup glyphs using TTGlyphPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    
    # .notdef
    p = TTGlyphPen(None)
    p.moveTo((50, 50))
    p.lineTo((150, 50))
    p.lineTo((150, 150))
    p.lineTo((50, 150))
    p.closePath()
    notdef_g = p.glyph()
    
    # space
    p = TTGlyphPen(None)
    space_g = p.glyph()
    
    # cross
    p = TTGlyphPen(None)
    # vertical
    p.moveTo((506, 0))
    p.lineTo((518, 0))
    p.lineTo((518, 1024))
    p.lineTo((506, 1024))
    p.closePath()
    # horizontal
    p.moveTo((0, 506))
    p.lineTo((1024, 506))
    p.lineTo((1024, 518))
    p.lineTo((0, 518))
    p.closePath()
    cross_g = p.glyph()
    
    glyphs_obj = {
        ".notdef": notdef_g,
        "space": space_g,
        "cross": cross_g
    }
    
    # Convert list of points to TrueType contours
    # In FontBuilder, we can pass points as TrueType points or use a pen.
    # fontBuilder.setupGlyf takes a dict of glyph names to glyph objects or contour lists.
    # Let's check how fontBuilder.setupGlyf expects data.
    # Usually it expects fontTools.ttLib.tables._g_l_y_f.Glyph objects or something similar if using low level,
    # or if we use setupGlyf we can pass a dict of glyph data. Let's see if we can pass contours directly.
    # It takes contours as list of lists of (x,y,flag) or just (x,y).
    # Since we use FontBuilder, let's use its standard setup.
    
    fb.setupGlyphOrder([".notdef", "space", "cross"])
    fb.setupCharacterMap({
        0x0020: "space",
        0x2316: "cross"
    })
    
    # We need to create glyf table.
    fb.setupGlyf(glyphs_obj)
    
    # Setup metrics
    metrics = {
        ".notdef": (WIDTH, 0),
        "space": (WIDTH, 0),
        "cross": (WIDTH, 0),
    }
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=1024, descent=0)
    fb.setupOS2(sTypoAscender=1024, sTypoDescender=0, usWinAscent=1024, usWinDescent=0)
    fb.setupPost()
    fb.setupNameTable({
        0: "Test Font",
        1: "test_font",
        4: "Test Font",
        6: "TestFont"
    })
    
    # Add axes
    axes = [
        ("CKRN", 0, 0, 1, "Control Axis"),
        ("XKRN", 0, 1, 1, "X Kern"), # Default 1 to represent on the right
        ("YKRN", 0, 0, 1, "Y Kern"), # Default 0
    ]
    fb.setupFvar(axes, [])
    
    # Setup GPOS with variable kerning
    # We want a SinglePos or PairPos. User wants PairPos for (cross, cross).
    # Value1: XAdvance
    # Value2: YPlacement
    # Let's create a GPOS table.
    
    # Custom GPOS table binary
    from fontTools.ttLib.tables.DefaultTable import DefaultTable
    class table_custom_GPOS(DefaultTable):
        def __init__(self, data):
            self.data = data
        def compile(self, font):
            return self.data
        def decompile(self, data, font):
            self.data = data
            
    # Glyphs: .notdef (0), space (1), cross (2)
    # We want a kerning pair (space, cross) with YPlacement variation using YKRN axis.
    # We will use VarStore in GDEF (which we define later).
    # Since we have only 1 row in our VarStore, we point to OuterIndex 0, InnerIndex 0.
    
    gpos_binary = bytearray()
    
    # 0: Header
    gpos_binary += struct.pack(">LHHH", 0x00010000, 10, 30, 44)
    
    # 10: ScriptList
    gpos_binary += struct.pack(">H", 1) # count
    gpos_binary += b'DFLT'
    gpos_binary += struct.pack(">H", 8) # offset to ScriptTable (relative to 10) -> 18
    
    # 18: ScriptTable
    gpos_binary += struct.pack(">HH", 4, 0) # offset to DefaultLangSys (relative to 18) -> 22, count 0
    
    # 22: DefaultLangSys
    gpos_binary += struct.pack(">HHH", 0, 0xFFFF, 1) # lookupOrder (0), reqFeature (65535), FeatureCount (1)
    gpos_binary += struct.pack(">H", 0) # Feature 0
    
    # 30: FeatureList
    gpos_binary += struct.pack(">H", 1) # count
    gpos_binary += b'kern'
    gpos_binary += struct.pack(">H", 8) # offset to FeatureTable (relative to 30) -> 38
    
    # 38: FeatureTable
    gpos_binary += struct.pack(">HH", 0, 1) # FeatureParams (0), LookupCount (1)
    gpos_binary += struct.pack(">H", 0) # Lookup 0
    
    # 44: LookupList
    gpos_binary += struct.pack(">H", 1) # count
    gpos_binary += struct.pack(">H", 4) # offset (relative to 44) -> 48
    
    # 48: LookupTable
    gpos_binary += struct.pack(">HHH", 2, 0, 1) # type 2 (PairPos), flag 0, count 1
    gpos_binary += struct.pack(">H", 8) # subtable offset (relative to 48) -> 56
    
    # 56: PairPosFormat1
    gpos_binary += struct.pack(">HHHH", 1, 12, 0, 0x0033) # format 1, cov_offset (relative to 56) -> 68, format1 0, format2 51 (XPlacement+YPlacement+Devices)
    gpos_binary += struct.pack(">HH", 1, 18) # pairsetcount 1, offset (relative to 56) -> 74
    
    # 68: Coverage (Format 1)
    gpos_binary += struct.pack(">HHH", 1, 1, 2) # format 1, count 1, glyph 'cross' (2)
    
    # 74: PairSet
    gpos_binary += struct.pack(">HH", 1, 2) # count 1, glyph 'cross' (2)
    # ValueRecord (XPlacement, YPlacement, XPlaDevice, YPlaDevice)
    gpos_binary += struct.pack(">HHHH", 0, 0, 12, 18) # XPlacement 0, YPlacement 0, XDevice offset 12 (relative to 74) -> 86, YDevice offset 18 (relative to 74) -> 92
    
    # 86: Device Table for XPlacement (Format 0x8000 for VariationDevice)
    gpos_binary += struct.pack(">HHH", 0, 1, 0x8000) # outer 0, inner 1 (points to Row 1 of GDEF VarStore), format 0x8000
    
    # 92: Device Table for YPlacement (Format 0x8000 for VariationDevice)
    gpos_binary += struct.pack(">HHH", 0, 0, 0x8000) # outer 0, inner 0 (points to Row 0 of GDEF VarStore), format 0x8000
    
    fb.font["GPOS"] = table_custom_GPOS(bytes(gpos_binary))
    
    # Now variable GPOS!
    # We need to add VariationStore to GPOS.
    # To do this, we need to set ValueFormat to include VariationDevice (Device/Variation)
    # ValueFormat1 = 4 (XAdvance) + 0x0040 (XAdvance Device) -> No, ValueFormat definitions:
    # 0x0001 XPlacement
    # 0x0002 YPlacement
    # 0x0004 XAdvance
    # 0x0008 YAdvance
    # 0x0010 XPlacement Device
    # 0x0020 YPlacement Device
    # 0x0040 XAdvance Device
    # 0x0080 YAdvance Device
    # So if we want variable XAdvance, we use ValueFormat1 = 0x0004 | 0x0040 = 0x0044.
    # If we want variable YPlacement, we use ValueFormat2 = 0x0002 | 0x0020 = 0x0022.
    # Wait, variable kerning can also use ValueFormat = 0x0004 (for simple PairPos format 2 class based where we don't use device tables, but if we want per-glyph-pair variable kerning, we use Format 1 and Device tables).
    # Let's use simple Device tables pointing to VarStore.
    
    # Set up VarStore for SinglePos
    # We want YPlacement of SinglePos to be driven by YKRN.
    # So we need one Variation Index.
    # Index 1: XKRN axis (no effect for YPlacement).
    # Index 2: YKRN axis (Max shift 100).
    
    locations = [
        {}, 
        {"XKRN": 1.0}, # Fixed from -1.0 to 1.0 (positive master)
        {"YKRN": 1.0},
    ]
    # Variation Model
    model = VariationModel(locations, axisOrder=["CKRN", "XKRN", "YKRN"])
    
    # Now deltas for XAdvance(Value1) and YPlacement(Value2).
    # - XAdvance should be driven by XKRN.
    #   When XKRN=1, shift = Max_Shift (say 100).
    #   When XKRN=0, shift = 0.
    #   So master values for XAdvance: [100, 0].
    # - YPlacement should be driven by YKRN.
    #   When YKRN=1, shift = Max_Shift (say 100).
    #   When YKRN=0, shift = 0.
    #   So master values for YPlacement: [0, 100].
    
    # FontBuilder/VarLib builder can build ItemVariationStore.
    # We need to pass the deltas for each "item" (ValueRecord).
    # Item 1: Value1 XAdvance Device
    # Item 2: Value2 YPlacement Device
    
    # Delta values for Item 1 (XAdvance): [Location1Value, Location2Value]
    # Location 1: XKRN=1. Value should be 100.
    # Location 2: YKRN=1. Value should be 0.
    # So deltas for Item 1 are [100, 0].
    
    # Delta values for Item 2 (YPlacement):
    # Location 1: XKRN=1. Value should be 0.
    # Location 2: YKRN=1. Value should be 100.
    # So deltas for Item 2 are [0, 100].
    
    # Using lower level tools
    regionList = buildVarRegionList(model.supports, ["CKRN", "XKRN", "YKRN"])
    
    # Values for Item (Master values for [base, loc1_XKRN_min, loc2_YKRN_max])
    # Item 1 (YPlacement): base 0, loc1 0, loc2 100
    
    x_deltas_raw = model.getDeltas([0, -1024, 0])[1:] # Base 0, XKRN_max=-1024, YKRN_max=0
    y_deltas_raw = model.getDeltas([0, 0, 1024])[1:] # Base 0, XKRN_max=0, YKRN_max=1024
    
    varData = buildVarData([1, 2], [y_deltas_raw, x_deltas_raw]) # Row 0 is Y, Row 1 is X
    varStore = buildVarStore(regionList, [varData])
    
    # Set VarStore in GDEF version 1.3!
    gdef = ot.GDEF()
    gdef.Version = 0x00010003
    gdef.VarStore = varStore
    
    fb.font["GDEF"] = newTable("GDEF")
    fb.font["GDEF"].table = gdef
    
    # Indices for assigning to devices
    varDataIndices = [(0, 0)] # Outer 0, Inner 0 for YPlacement
    
    # Now assign the indices to the ValueRecords
    # ValueFormat Device implies we set XAdvanceDevice to a VariationClass or Device table (if old) or VarIdx.
    # In OT 1.8, we use VariationDevice (Format 0x8000).
    # In fontTools.ttLib.tables.otTables, we use ot.Device() with Format=0x8000 and Setting the Outer and Inner indices.
    
    # GPOS is now handled manually above.
    
    
    # 4. Now add avar2!
    # We will write the binary table for 'avar' version 2 manually if fontTools doesn't support it.
    # Wait, let's see if we can create an ItemVariationStore for avar2!
    # avar2 ItemVariationStore maps axis indices mapping.
    # We have 3 axes: CKRN (0), XKRN (1), YKRN (2).
    # We want CKRN to drive XKRN and YKRN non-linearly.
    # Specifically, when CKRN varies from 0 to 1, we want XKRN to go from 1 to 0 (quarter circle) and YKRN from 0 to 1.
    #
    # Mapping points for XKRN (driven by CKRN):
    # CKRN = 0.0 -> XKRN_delta = 1.0
    # CKRN = 0.5 -> XKRN_delta = 0.707
    # CKRN = 1.0 -> XKRN_delta = 0.0
    #
    # Mapping points for YKRN (driven by CKRN):
    # CKRN = 0.0 -> YKRN_delta = 0.0
    # CKRN = 0.5 -> YKRN_delta = 0.707
    # CKRN = 1.0 -> YKRN_delta = 1.0
    #
    # Let's define the VariationModel for the avar2 VarStore.
    # The input to this model is just CKRN! Because CKRN is the user axis.
    # Locations for CKRN:
    # default is 0.
    # Min = 0, Max = 1.
    # Locations:
    # master 1: CKRN = 0.5 (Region 0 to 1, peak 0.5) -> wait, peak can be at 1.0 or 0.5.
    # Let's use 2 masters for CKRN:
    # m1: {CKRN: 0.5} (Peak at 0.5, span 0 to 1)
    # m2: {CKRN: 1.0} (Peak at 1.0, span 0 to 1)
    #
    # At CKRN = 0, initial values are CKRN=0, XKRN=0, YKRN=0.
    # We want final values: XKRN=1, YKRN=0.
    # So we need a delta at CKRN=0 that sets XKRN to 1!
    # Can we have a delta at the default location?
    # In OpenType variations, the default location is the base. Deltas at default are 0 by definition!
    # If default CKRN = 0, we can't have a non-zero delta at CKRN=0.
    # This means set initial coordinates: CKRN=0, XKRN=1, YKRN=0.
    # If we set default XKRN to 1, then at CKRN=0 we get XKRN=1 (default).
    # Then as CKRN increases to 1, we want XKRN to drop to 0. So we apply negative deltas!
    # Let's make default XKRN = 1, and default YKRN = 0.
    # Then at default (CKRN=0): XKRN = 1, YKRN = 0. Perfect!
    # Now as CKRN goes to 1:
    # At CKRN=0.5: we want XKRN = 0.707, YKRN = 0.707.
    # Delas relative to default (1, 0):
    # XKRN delta = 0.707 - 1 = -0.293
    # YKRN delta = 0.707 - 0 = +0.707
    #
    # At CKRN=1.0: we want XKRN = 0, YKRN = 1.0.
    # Deltas relative to default (1, 0):
    # XKRN delta = 0 - 1 = -1.0
    # YKRN delta = 1.0 - 0 = +1.0
    #
    # This is much easier! Default is (XKRN=1, YKRN=0).
    # We only need deltas for CKRN > 0.
    # Locations for model:
    # Loc 1: CKRN = 0.5
    # Loc 2: CKRN = 1.0
    #
    avar_locs = [{}]
    for i in range(1, 9):
        avar_locs.append({"CKRN": i / 8.0})
    avar_model = VariationModel(avar_locs, axisOrder=["CKRN"])
    
    # Deltas for XKRN (internal axis index 1):
    # Values at Loc 1 (0.5) and Loc 2 (1.0):
    # m1 (CKRN=0.5): we want XKRN = 0.707. Default is 1. Value relative to default is -0.293.
    # m2 (CKRN=1.0): we want XKRN = 0. Default is 1. Value relative to default is -1.0.
    # Master values for XKRN: [-0.293, -1.0]
    
    # Deltas for YKRN (internal axis index 2):
    # m1 (CKRN=0.5): we want YKRN = 0.707. Default is 0. Value relative to default is +0.707.
    # m2 (CKRN=1.0): we want YKRN = 1.0. Default is 0. Value relative to default is +1.0.
    # Master values for YKRN: [+0.707, +1.0]
    
    
    # Using lower level tools for avar2
    avar_regionList = buildVarRegionList(avar_model.supports[1:], ["CKRN", "XKRN", "YKRN"])
    
    # Items for avar2
    # Item 0 (CKRN): 0 deltas
    # Item 1 (XKRN): computed deltas
    # Item 2 (YKRN): computed deltas
    
    import math
    vals_X = [0.0]
    vals_Y = [0.0]
    for i in range(1, 9):
        theta = (i / 8.0) * (math.pi / 2)
        vals_X.append(1 - math.cos(theta))
        vals_Y.append(math.sin(theta))
        
    deltas_XKRN_raw = avar_model.getDeltas(vals_X)[1:]
    deltas_YKRN_raw = avar_model.getDeltas(vals_Y)[1:]
    deltas_CKRN_raw = avar_model.getDeltas([0.0] * 9)[1:]
    
    deltas_CKRN_int = [int(round(d * 16384)) for d in deltas_CKRN_raw]
    deltas_XKRN_int = [int(round(d * 16384)) for d in deltas_XKRN_raw]
    deltas_YKRN_int = [int(round(d * 16384)) for d in deltas_YKRN_raw]
    
    avar_varData = buildVarData(list(range(8)), [ # Region indices 0 to 7
        deltas_CKRN_int,
        deltas_XKRN_int,
        deltas_YKRN_int
    ])
    
    avar_varStore = buildVarStore(avar_regionList, [avar_varData])
    
    # Use manual identity DeltaSetIndexMap (4 bytes of zeros)
    map_data = b'\x00\x00\x00\x00'
    
    writer_store = OTTableWriter()
    avar_varStore.compile(writer_store, fb.font)
    store_data = writer_store.getAllData()
    
    binary_data = bytearray()
    # Header: Version 2.0 (4 bytes), reserved (2 bytes), axisCount (2 bytes)
    binary_data += struct.pack(">LHH", 0x00020000, 0, 3)
    
    # SegmentMaps for 3 axes (identity mapping).
    for _ in range(3):
        binary_data += struct.pack(">H", 3) # count
        binary_data += struct.pack(">HH", 0xC000, 0xC000) # (-1, -1)
        binary_data += struct.pack(">HH", 0x0000, 0x0000) # (0, 0)
        binary_data += struct.pack(">HH", 0x4000, 0x4000) # (1, 1)
        
    # Offsets
    varIdxMap_offset = 58
    varStore_offset = 58 + len(map_data)
    
    binary_data += struct.pack(">LL", varIdxMap_offset, varStore_offset)
    binary_data += map_data
    binary_data += store_data
    
    # Define custom table class to bypass fontTools avar1 validation
    from fontTools.ttLib.tables.DefaultTable import DefaultTable
    class table_custom_avar(DefaultTable):
        def __init__(self, data):
            self.data = data
        def compile(self, font):
            return self.data
        def decompile(self, data, font):
            self.data = data
            
    fb.font["avar"] = table_custom_avar(binary_data)
    
    fb.save("avar2_kern_test.ttf")
    print("Font saved as avar2_kern_test.ttf")

if __name__ == "__main__":
    main()
