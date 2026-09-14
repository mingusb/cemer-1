// Exercise the application's actual dump-path cache without loading a GUI.
#include <DumpPathTokenList>
#include <double_Matrix>
#include <dumpMisc>
#include <taMisc>
#include <taNBase>
#include <taSigLink>
#include <QCoreApplication>
#include <iostream>
#include <memory>
#include <new>
#include <stdexcept>

namespace {
void require(bool value, const char* text) {
  if (!value) throw std::runtime_error(text);
}
taBase* resolve(DumpPathTokenList& tokens, const char* value) {
  String path(value);
  return tokens.FindFromPath(path, &TA_taBase, nullptr);
}
void lifetime(int streamVersion) {
  taMisc::strm_ver = streamVersion;
  DumpPathTokenList tokens;
  tokens.ReInit();
  auto object = std::make_unique<taNBase>();
  const int references = taBase::GetRefn(object.get());
  DumpPathToken* token = tokens.AddObjPath(object.get(), ".original");
  const char* path = streamVersion < 3 ? "$0$" : "$.original$";
  require(resolve(tokens, path) == object.get(), "Live token did not resolve");
  require(tokens.FindObj(object.get()) == 0, "Live object hash lookup failed");
  require(taBase::GetRefn(object.get()) == references, "Token acquired object ownership");
  object.reset();
  require(token->object == nullptr, "Destroyed object remains in path token");
  require(resolve(tokens, path) == nullptr, "Destroyed object was returned from path token");
  tokens.Reset();
  std::cout << "stream version " << streamVersion << ": live/deleted/non-owning references PASS\n";
}
void addressReuse() {
  taMisc::strm_ver = 3;
  DumpPathTokenList tokens;
  tokens.ReInit();
  alignas(taNBase) unsigned char storage[sizeof(taNBase)];
  taNBase* first = ::new (storage) taNBase;
  tokens.AddObjPath(first, ".first");
  first->~taNBase();
  taNBase* second = ::new (storage) taNBase;
  const bool rejected = tokens.FindObj(second) == -1;
  tokens.AddObjPath(second, ".second");
  const bool fresh = tokens.FindObj(second) == 1 &&
                     resolve(tokens, "$.second$") == second &&
                     resolve(tokens, "$.first$") == nullptr;
  tokens.Reset();
  const bool detached = second->sig_link() == nullptr ||
                        second->sig_link()->clients_list().size == 0;
  second->~taNBase();
  require(rejected, "Reused address matched the destroyed object's token");
  require(fresh, "Reused address did not receive a fresh token");
  require(detached, "Cache reset retained a signal client on the live object");
  std::cout << "reused address and live-object cache reset PASS\n";
}
void untrackablePath() {
  taMisc::strm_ver = 3;
  double_Matrix matrix;
  taBase* previousRoot = dumpMisc::dump_root;
  dumpMisc::dump_root = &matrix;
  DumpPathTokenList tokens;
  tokens.ReInit();
  require(matrix.geom.GetSigLink() == nullptr, "Fixture unexpectedly supports weak references");
  tokens.AddObjPath(&matrix.geom, ".geom");
  const bool resolved = resolve(tokens, "$.geom$") == &matrix.geom;
  tokens.Reset();
  dumpMisc::dump_root = previousRoot;
  require(resolved, "Untrackable embedded object lost path resolution");
  std::cout << "signal-less embedded MatrixGeom path resolution PASS\n";
}
}
int main(int argc, char** argv) {
  QCoreApplication application(argc, argv);
  taMisc::use_gui = false;
  taMisc::Init_Types();
  try {
    lifetime(2);
    lifetime(3);
    addressReuse();
    untrackablePath();
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
  return 0;
}
