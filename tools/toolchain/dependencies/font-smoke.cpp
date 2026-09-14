#include <ft2build.h>
#include FT_FREETYPE_H
#include <hb-ft.h>
#include <cstdio>
#include <cstring>

int main(int argc, char** argv) {
  const char* path = argc > 1 ? argv[1] : "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf";
  FT_Library library = nullptr;
  FT_Face face = nullptr;
  if (FT_Init_FreeType(&library) || FT_New_Face(library, path, 0, &face) ||
      FT_Set_Char_Size(face, 0, 32 * 64, 72, 72)) return 1;
  hb_font_t* font = hb_ft_font_create_referenced(face);
  const char* samples[] = {"office", "Ελληνικά", "العربية"};
  bool passed = true;
  for (const char* sample : samples) {
    hb_buffer_t* buffer = hb_buffer_create();
    hb_buffer_add_utf8(buffer, sample, -1, 0, -1);
    hb_buffer_guess_segment_properties(buffer);
    hb_shape(font, buffer, nullptr, 0);
    unsigned count = 0;
    const auto* glyphs = hb_buffer_get_glyph_infos(buffer, &count);
    const auto* positions = hb_buffer_get_glyph_positions(buffer, nullptr);
    passed = passed && count > 0;
    long advance = 0;
    for (unsigned i = 0; i < count; ++i) {
      passed = passed && glyphs[i].codepoint != 0;
      advance += positions[i].x_advance;
    }
    passed = passed && advance > 0;
    if (std::strcmp(sample, "office") == 0) passed = passed && count < 6;
    std::printf("%s: %u glyphs, advance %ld\n", sample, count, advance);
    hb_buffer_destroy(buffer);
  }
  hb_font_destroy(font);
  FT_Done_Face(face);
  FT_Done_FreeType(library);
  return passed ? 0 : 1;
}
