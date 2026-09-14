// Exercise the application's actual wrapper using an isolated local repository.
#include <SubversionClient>
#include <String_PArray>
#include <QCoreApplication>
#include <QProcess>
#include <QTemporaryDir>
#include <QUrl>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool condition, const char *message) {
  if (!condition) throw std::runtime_error(message);
}
void write(const String& path, const char *text) {
  std::ofstream stream(path.chars());
  stream << text;
  require(stream.good(), "Could not write working-copy file");
}
}

int main(int argc, char **argv) {
  QCoreApplication application(argc, argv);
  QTemporaryDir temporary;
  try {
    require(temporary.isValid(), "Could not create test directory");
    const QString repository = temporary.path() + "/repository";
    const QString workingCopy = temporary.path() + "/working-copy";
    require(QProcess::execute("svnadmin", {"create", repository}) == 0,
            "Could not create repository");
    const String url(QUrl::fromLocalFile(repository).toString().toUtf8().constData());
    const String wc(workingCopy.toUtf8().constData());
    const String original = wc + "/original.txt";
    const String copied = wc + "/copied.txt";
    String moved = wc + "/moved.txt";
    SubversionClient client;
    require(client.Checkout(url, wc) == 0, "Empty checkout revision");
    write(original, "original\n");
    client.Add(original);
    require(client.Checkin("first\r\nsecond\rthird") == 1, "Initial commit");
    require(client.Checkin("no changes") == -1, "No-op commit");

    String_PArray paths;
    paths.Add(original);
    String copyDestination = copied;
    client.CopyFile(paths, copyDestination);
    paths.Reset();
    paths.Add(copied);
    client.MoveFile(paths, moved);
    client.MakeDir(wc + "/directory");
    require(client.Checkin("copy, move and mkdir") == 2, "Second commit");
    require(std::filesystem::exists(moved.chars()), "Move target missing");

    String contents;
    client.GetFile(url + "/moved.txt", contents);
    require(contents == "original\n", "Repository file contents");
    write(original, "modified\n");
    String diff;
    client.GetDiffWc(original, diff);
    require(diff.contains("modified"), "Working-copy diff");
    paths.Reset();
    paths.Add(original);
    client.RevertFiles(paths);
    require(client.GetLastChangedRevision(original) == 1, "Changed revision");

    int revision = -1, kind = -1, changed = -1, date = -1;
    int64_t size = -1;
    String root, author;
    require(client.GetInfo(original, revision, kind, root, changed, date, author, size),
            "Working-copy info");
    require(root == url + "/original.txt" && changed == 1, "Repository metadata");
    client.GetRootUrlFromPath(root, original);
    require(root == url, "Repository root lookup");
    client.Cleanup();
    paths.Reset();
    paths.Add(moved);
    client.Delete(paths, false, false);
    require(client.Checkin("delete moved file") == 3, "Delete commit");
    std::cout << "SubversionClient checkout/add/commit/copy/move/mkdir/cat/diff/"
                 "revert/info/root/cleanup/delete checks passed\n";
  } catch (const std::exception& error) {
    temporary.setAutoRemove(false);
    std::cerr << error.what() << "; retained "
              << temporary.path().toStdString() << '\n';
    return 1;
  }
  return 0;
}
