// Exercise real taFiler cleanup after failed opens without creating a GUI.
#include <taFiler>
#include <QCoreApplication>
#include <QTemporaryDir>
#include <fstream>
#include <iostream>
#include <stdexcept>

class FilerProbe : public taFiler {
public:
  FilerProbe() : taFiler(NO_FLAGS) {}
  ~FilerProbe() override = default;
  void attach(std::fstream *stream) {
    Close();
    fstrm = stream;
    ostrm = stream;
  }
  std::fstream& stream() { return *fstrm; }
};

static void require(bool condition, const char *message) {
  if (!condition) throw std::runtime_error(message);
}

int main(int argc, char **argv) {
  QCoreApplication application(argc, argv);
  try {
    QTemporaryDir directory;
    require(directory.isValid(), "Could not create test directory");
    FilerProbe filer;
    require(!filer.FlushOutStream(), "Empty filer unexpectedly flushed");
    filer.attach(new std::fstream);
    require(!filer.FlushOutStream(), "Unopened stream unexpectedly flushed");
    filer.Close();
    filer.Close();
    const std::string missing = directory.filePath("missing/file.txt").toStdString();
    filer.attach(new std::fstream(missing, std::ios::out));
    require(!filer.stream().is_open(), "Failed-open fixture unexpectedly opened");
    require(!filer.FlushOutStream(), "Failed-open stream unexpectedly flushed");
    filer.Close();
    const std::string valid = directory.filePath("valid.txt").toStdString();
    filer.attach(new std::fstream(valid, std::ios::out));
    require(filer.stream().is_open(), "Valid file did not open");
    filer.stream() << "stream recovery\n" << std::flush;
    require(filer.FlushOutStream(), "Open file did not flush");
    filer.stream().setstate(std::ios::badbit);
    require(filer.FlushOutStream(), "Open file with badbit lost descriptor access");
    filer.stream().clear();
    filer.stream().close();
    require(!filer.FlushOutStream(), "Explicitly closed file unexpectedly flushed");
    filer.Close();
    std::ifstream input(valid);
    std::string text;
    std::getline(input, text);
    require(text == "stream recovery", "Recovered file contents changed");
    std::cout << "taFiler absent/unopened/failed/open/badbit/closed streams and repeated cleanup passed\n";
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
  return 0;
}
