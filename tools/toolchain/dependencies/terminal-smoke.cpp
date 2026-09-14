// Exercise the installed terminal libraries through their public APIs.
#include <ncursesw/curses.h>
#include <ncursesw/panel.h>
#include <readline/history.h>
#include <readline/readline.h>

#include <clocale>
#include <cstdio>
#include <cstdlib>
#include <cstring>

static int input_index = 0;
static int scripted_input(FILE*) {
  const char input[] = "stack\n";
  return input_index < 6 ? input[input_index++] : EOF;
}

int main() {
  if(!std::setlocale(LC_ALL, "C.UTF-8")) return 1;
  FILE* input = std::tmpfile();
  FILE* output = std::tmpfile();
  if(!input || !output) return 2;
  SCREEN* screen = newterm("xterm-256color", output, input);
  if(!screen) return 3;
  WINDOW* window = newwin(4, 20, 0, 0);
  if(!window || mvwaddwstr(window, 0, 0, L"Qt λ") == ERR) return 4;
  cchar_t cell{};
  wchar_t characters[CCHARW_MAX]{};
  attr_t attributes{};
  short pair{};
  if(mvwin_wch(window, 0, 3, &cell) == ERR ||
     getcchar(&cell, characters, &attributes, &pair, nullptr) == ERR ||
     characters[0] != L'λ') return 5;
  PANEL* panel = new_panel(window);
  if(!panel || hide_panel(panel) == ERR || !panel_hidden(panel) ||
     show_panel(panel) == ERR || panel_window(panel) != window) return 6;
  update_panels();
  doupdate();
  del_panel(panel);
  delwin(window);
  endwin();
  delscreen(screen);
  std::fclose(input);
  std::fclose(output);

  using_history();
  clear_history();
  add_history("first command");
  add_history("second command");
  char* expansion = nullptr;
  if(history_expand("!!", &expansion) != 1 || !expansion ||
     std::strcmp(expansion, "second command") != 0) return 7;
  std::free(expansion);
  clear_history();

  FILE* readline_output = std::tmpfile();
  if(!readline_output) return 8;
  rl_outstream = readline_output;
  rl_getc_function = scripted_input;
  char* line = readline("emergent> ");
  if(!line || std::strcmp(line, "stack") != 0) return 9;
  std::free(line);
  std::fclose(readline_output);
  rl_outstream = stdout;
  std::printf("PASS wide-character window, panel lifecycle, history expansion, readline input\nncurses=%s\nreadline=%s\n",
              curses_version(), rl_library_version);
}
