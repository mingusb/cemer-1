// Exercise the library implementation with real state objects and exact logical allocations.
#include <LayerState_cpp>
#include <UnitState_cpp>
#include <UnGpState_cpp>
#include <QCoreApplication>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
void require(bool value, const char* text) {
  if (!value) throw std::runtime_error(text);
}
void check(const char* name, int ux, int uy, int unitsPerGroup,
           int gx, int gy, int groups) {
  const int unitsCount = unitsPerGroup * (groups ? groups : 1);
  NetworkState_cpp net;
  LayerState_cpp layer;
  std::vector<UnitState_cpp> units(static_cast<size_t>(unitsCount));
  std::vector<UnGpState_cpp> unitGroups(static_cast<size_t>(groups + 1));
  std::vector<int> threadForUnit(static_cast<size_t>(unitsCount + 1), 0);
  std::vector<int> threadUnitIndex(static_cast<size_t>(unitsCount + 1));
  for (int i = 0; i < unitsCount; ++i) {
    threadUnitIndex[static_cast<size_t>(i + 1)] = i;
    units[static_cast<size_t>(i)].lay_un_idx = -1;
    units[static_cast<size_t>(i)].ungp_un_idx = -1;
  }
  char* unitMemory = reinterpret_cast<char*>(units.data());
  net.n_units = unitsCount;
  net.n_units_built = unitsCount + 1;
  net.n_ungps_built = groups + 1;
  net.n_thrs_built = 1;
  net.unit_state_size = sizeof(UnitState_cpp);
  net.ungp_state_size = sizeof(UnGpState_cpp);
  net.units_thrs = threadForUnit.data();
  net.units_thr_un_idxs = threadUnitIndex.data();
  net.thrs_units_mem = &unitMemory;
  net.ungps_mem = reinterpret_cast<char*>(unitGroups.data());
  layer.Initialize_lay_core(0, -1, 0, 1, 0, unitsCount, groups);
  layer.Initialize_lay_geom(ux, uy, unitsPerGroup, gx, gy, groups,
                            ux * gx, uy * gy, unitsCount, 2, 3);
  layer.LayoutUnits(&net);
  require(layer.n_units == unitsCount && layer.n_ungps == groups,
          "logical allocation counts changed");
  require(layer.gp_geom_x == gx && layer.gp_geom_y == gy,
          "display grid dimensions changed");
  for (int i = 0; i < unitsCount; ++i) {
    const int group = groups ? i / unitsPerGroup : -1;
    const int local = groups ? i % unitsPerGroup : i;
    const UnitState_cpp& unit = units[static_cast<size_t>(i)];
    require(unit.lay_un_idx == i, "flat unit index changed");
    require(unit.gp_idx == group, "group index changed");
    require(unit.ungp_un_idx == local, "local unit index changed");
    require(unit.pos_x == local % ux && unit.pos_y == local / ux,
            "local coordinates changed");
    const int expectedX = groups ? (group % gx) * (ux + 2) + local % ux : local % ux;
    const int expectedY = groups ? (group / gx) * (uy + 3) + local / ux : local / ux;
    require(unit.disp_pos_x == expectedX && unit.disp_pos_y == expectedY,
            "display coordinates changed");
  }
  for (int group = 0; group < groups; ++group) {
    const UnGpState_cpp& state = unitGroups[static_cast<size_t>(group + 1)];
    require(state.pos_x == (group % gx) * ux && state.pos_y == (group / gx) * uy,
            "group origin changed");
  }
  std::cout << name << ": " << unitsCount << " units in " << groups << " groups PASS\n";
}
}
int main(int argc, char** argv) {
  QCoreApplication application(argc, argv);
  try {
    check("rectangular baseline", 2, 3, 6, 2, 2, 4);
    check("id_ed partial group grid", 1, 4, 4, 3, 1, 2);
    check("partial multirow group grid", 2, 2, 4, 3, 2, 4);
    check("partial unit grids within groups", 3, 2, 5, 2, 1, 2);
    check("partial units and groups", 3, 2, 5, 3, 2, 4);
    check("ungrouped partial unit grid", 3, 2, 5, 0, 0, 0);
    check("ungrouped rectangular baseline", 3, 2, 6, 0, 0, 0);
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
  return 0;
}
