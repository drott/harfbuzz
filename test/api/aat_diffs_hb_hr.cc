#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <cmath>
#include <hb.h>
#include <hb-ot.h>

// Helper to read the font file into a HarfBuzz blob
hb_blob_t* CreateBlobFromFile(const char* path) {
  FILE* f = fopen(path, "rb");
  if (!f) return nullptr;
  fseek(f, 0, SEEK_END);
  long size = ftell(f);
  fseek(f, 0, SEEK_SET);
  char* data = (char*)malloc(size);
  long read = fread(data, 1, size, f);
  fclose(f);
  if (read != size) {
    free(data);
    return nullptr;
  }
  return hb_blob_create(data, size, HB_MEMORY_MODE_READONLY, data, free);
}

void RunShaping(hb_font_t* font, const char* text, const char* shaper_name, 
                float* advances, unsigned int* glyph_count_out) {
  hb_buffer_t* buffer = hb_buffer_create();
  hb_buffer_add_utf8(buffer, text, -1, 0, -1);
  hb_buffer_set_direction(buffer, HB_DIRECTION_LTR);
  hb_buffer_set_script(buffer, HB_SCRIPT_LATIN);
  hb_buffer_set_language(buffer, hb_language_from_string("en", -1));

  const char* shapers[] = {shaper_name, nullptr};
  hb_shape_full(font, buffer, nullptr, 0, shapers);

  unsigned int count;
  hb_glyph_position_t* pos = hb_buffer_get_glyph_positions(buffer, &count);

  *glyph_count_out = count;
  for (unsigned int i = 0; i < count; ++i) {
    // Convert 16.16 fixed point advance to floating-point pixels
    advances[i] = (float)pos[i].x_advance / 65536.0f;
  }

  hb_buffer_destroy(buffer);
}

int main() {
  const char* font_path = "/System/Library/Fonts/SFNSItalic.ttf";
  printf("Starting HarfBuzz Standalone Demonstrator...\n");
  printf("Loading font from: %s\n", font_path);

  hb_blob_t* blob = CreateBlobFromFile(font_path);
  if (!blob) {
    fprintf(stderr, "Error: Failed to read SFNSItalic.ttf from /System/Library/Fonts/\n");
    return 1;
  }

  hb_face_t* face = hb_face_create(blob, 0);
  if (hb_face_get_glyph_count(face) == 0) {
    fprintf(stderr, "Error: Loaded face has 0 glyphs (invalid font)\n");
    hb_face_destroy(face);
    hb_blob_destroy(blob);
    return 1;
  }

  printf("Font face loaded successfully.\n\n");

  for (int weight = 100; weight <= 900; weight += 100) {
    printf("--- WEIGHT %d ---\n", weight);

    hb_font_t* font = hb_font_create(face);
    hb_ot_font_set_funcs(font);

    // Set scale factor matching SkiaScalarToHarfBuzzPosition in Blink (16.16 fixed-point)
    float size_px = 20.0f;
    int scale = (int)(size_px * 65536.0f);
    hb_font_set_scale(font, scale, scale);

    // Set ptem size critical for CoreText tracking/trak table
    hb_font_set_ptem(font, size_px);

    // Set weight variation axis matching Skia/CoreText layout
    hb_variation_t var;
    var.tag = HB_TAG('w', 'g', 'h', 't');
    var.value = (float)weight;
    hb_font_set_variations(font, &var, 1);

    char text[64];
    snprintf(text, sizeof(text), "System italic font at weight %d", weight);
    printf("Text: \"%s\"\n", text);

    float ot_advances[128] = {0};
    float rust_advances[128] = {0};
    unsigned int ot_count = 0;
    unsigned int rust_count = 0;

    // Run standard OpenType C++ shaper
    RunShaping(font, text, "ot", ot_advances, &ot_count);

    // Run HarfRust shaper
    RunShaping(font, text, "harfrust", rust_advances, &rust_count);

    if (ot_count != rust_count) {
      printf("  [WARNING] Glyph count mismatch! ot = %u, harfrust = %u\n", ot_count, rust_count);
    }

    unsigned int compare_count = ot_count < rust_count ? ot_count : rust_count;
    bool has_differences = false;

    for (unsigned int i = 0; i < compare_count; ++i) {
      float diff = rust_advances[i] - ot_advances[i];
      if (std::abs(diff) > 0.001f) {
        has_differences = true;
        float ot_third = std::round(ot_advances[i] * 3.0f) / 3.0f;
        float rust_third = std::round(rust_advances[i] * 3.0f) / 3.0f;
        float ot_fourth = std::round(ot_advances[i] * 4.0f) / 4.0f;
        float rust_fourth = std::round(rust_advances[i] * 4.0f) / 4.0f;

        printf("  Glyph %2u: C++ (\"ot\") = %.4f, Rust (\"harfrust\") = %.4f (diff = %+.4f)\n",
               i, ot_advances[i], rust_advances[i], diff);
        if (std::abs(rust_third - ot_third) > 0.001f) {
          printf("            1/3 px Snap: C++ = %.4f, Rust = %.4f (diff = %+.4f)\n",
                 ot_third, rust_third, rust_third - ot_third);
        }
        if (std::abs(rust_fourth - ot_fourth) > 0.001f) {
          printf("            1/4 px Snap: C++ = %.4f, Rust = %.4f (diff = %+.4f)\n",
                 ot_fourth, rust_fourth, rust_fourth - ot_fourth);
        }
      }
    }

    if (!has_differences) {
      printf("  [SUCCESS] All shaped advances match perfectly between C++ (\"ot\") and Rust (\"harfrust\")!\n");
    }
    printf("\n");

    hb_font_destroy(font);
  }

  hb_face_destroy(face);
  hb_blob_destroy(blob);
  printf("Standalone Demonstrator Completed.\n");
  return 0;
}
