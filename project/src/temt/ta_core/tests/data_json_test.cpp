// Exercise the actual table JSON API used by neural monitor clients.
#include <DataTable>
#include <taMisc>
#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool value, const char* message) {
  if(!value) throw std::runtime_error(message);
}
QJsonArray columns(DataTable& table, int first=0, int rows=-1) {
  QJsonObject result;
  require(table.GetDataAsJSON(result, "", first, rows), "JSON export failed");
  return result["result"].toObject()["columns"].toArray();
}
void vectorTypes() {
  DataTable table;
  table.NewColMatrix(DataCol::VT_FLOAT, "act", 1, 16);
  table.NewColMatrix(DataCol::VT_DOUBLE, "double", 1, 16);
  table.NewColMatrix(DataCol::VT_INT, "index", 1, 16);
  table.NewColMatrix(DataCol::VT_BYTE, "byte", 1, 16);
  table.NewColMatrix(DataCol::VT_BOOL, "mask", 1, 16);
  table.NewColMatrix(DataCol::VT_STRING, "names", 1, 16);
  table.NewColMatrix(DataCol::VT_VARIANT, "variant", 1, 16);
  table.AddRows(3);
  for(int row=0; row<3; ++row) {
    for(int cell=0; cell<16; ++cell) {
      const int index=16*row+cell;
      table.SetMatrixFlatVal(index/4.0, "act", row, cell);
      table.SetMatrixFlatVal(index/4.0, "double", row, cell);
      table.SetMatrixFlatVal(index-16, "index", row, cell);
      table.SetMatrixFlatVal(index, "byte", row, cell);
      table.SetMatrixFlatVal(bool(index%2), "mask", row, cell);
      table.SetMatrixFlatVal(String("unit ")+String(index), "names", row, cell);
      table.SetMatrixFlatVal(String("value ")+String(index), "variant", row, cell);
    }
  }
  const QJsonArray all=columns(table);
  require(all.size()==7, "JSON dropped a column");
  for(int col=0; col<7; ++col) {
    const QJsonObject object=all[col].toObject();
    require(object["matrix"].toBool(), "Vector matrix flag lost");
    require(object["dimensions"].toArray()==QJsonArray{16}, "Vector shape changed");
    require(object.contains("values"), "1D monitor values omitted from JSON");
    const QJsonArray rows=object["values"].toArray();
    require(rows.size()==3, "Vector row count changed");
    for(int row=0; row<3; ++row) {
      const QJsonArray cells=rows[row].toArray();
      require(cells.size()==16, "Vector length changed");
      for(int cell=0; cell<16; ++cell) {
        const int index=16*row+cell;
        QJsonValue expected;
        if(col<2) expected=index/4.0;
        else if(col==2) expected=index-16;
        else if(col==3) expected=index;
        else if(col==4) expected=bool(index%2);
        else expected=QString(col==5 ? "unit %1" : "value %1").arg(index);
        if(cells[cell]!=expected) {
          std::cerr << "column " << col << ", row " << row << ", cell " << cell
                    << ": actual " << QJsonDocument(QJsonArray{cells[cell]}).toJson().constData()
                    << "expected " << QJsonDocument(QJsonArray{expected}).toJson().constData();
          throw std::runtime_error("JSON changed a value or its JSON type");
        }
      }
    }
    const auto selected=columns(table,1,1)[col].toObject()["values"].toArray();
    require(selected==QJsonArray{rows[1]}, "Row slicing changed vector nesting");
    require(columns(table,-1,1)[col].toObject()["values"].toArray()==QJsonArray{rows[2]},
            "Negative row selection changed vector values");
    require(columns(table,3,0)[col].toObject()["values"].toArray().isEmpty(),
            "Empty row range returned vector values");
  }
  DataTable restored;
  QJsonObject output;
  require(table.GetDataAsJSON(output), "Roundtrip export failed");
  if(!restored.SetDataFromJSON(output)) {
    std::cerr << restored.json_error_msg.chars() << "\n";
    throw std::runtime_error("Vector JSON could not be imported");
  }
  require(columns(restored)==all, "Vector JSON roundtrip changed data");
  std::cout << "1D monitor values, types, row ranges and JSON roundtrip PASS\n";
}
void flatten(const QJsonArray& input, QJsonArray& output) {
  for(const auto& value : input) {
    if(value.isArray()) flatten(value.toArray(), output);
    else output.append(value);
  }
}
void booleanShapes() {
  for(int dims=0; dims<=4; ++dims) {
    DataTable table;
    DataCol* column = dims==0 ? table.NewCol(DataCol::VT_BOOL, "mask")
                             : table.NewColMatrix(DataCol::VT_BOOL, "mask", dims, 2, 2, 2, 2);
    require(column!=nullptr, "Boolean column creation failed");
    table.AddRows(3);
    const int cells=1<<dims;
    for(int row=0; row<3; ++row) {
      for(int cell=0; cell<cells; ++cell) {
        const bool expected=bool((row+cell)%2);
        if(dims==0) {
          require(table.SetVal(expected, "mask", row), "Boolean scalar write failed");
          require(column->GetValAsBool(row)==expected, "Boolean scalar accessor lost true");
        } else {
          require(table.SetMatrixFlatVal(expected, "mask", row, cell), "Boolean matrix write failed");
          require(column->GetValAsBoolM(row, cell)==expected, "Boolean matrix accessor lost true");
        }
      }
    }
    const QJsonArray all=columns(table);
    const QJsonArray rows=all[0].toObject()["values"].toArray();
    require(rows.size()==3, "Boolean JSON row count changed");
    for(int row=0; row<3; ++row) {
      QJsonArray flat;
      if(dims==0) flat.append(rows[row]);
      else flatten(rows[row].toArray(), flat);
      require(flat.size()==cells, "Boolean JSON matrix shape changed");
      for(int cell=0; cell<cells; ++cell) {
        require(flat[cell].isBool(), "Boolean JSON exported a number instead of a bool");
        require(flat[cell].toBool()==bool((row+cell)%2), "Boolean JSON lost true");
      }
    }
    DataTable restored;
    QJsonObject output;
    require(table.GetDataAsJSON(output), "Boolean JSON export failed");
    require(restored.SetDataFromJSON(output), "Boolean JSON import failed");
    require(columns(restored)==all, "Boolean JSON roundtrip changed data");
  }
  std::cout << "Boolean scalar and 1D-4D matrix accessors and JSON roundtrip PASS\n";
}
void importString() {
  const char* json=R"({"columns":[{"name":"cycle","type":"int","matrix":false,"values":[0,1,2]}]})";
  DataTable table;
  taMisc::last_err_msg="";
  table.ImportDataJSONString(json);
  require(taMisc::last_err_msg.empty(), "Valid JSON string emitted an error");
  require(table.rows==3 && table.GetVal("cycle",2).toInt()==2,
          "Valid JSON string did not import its data");
  std::cout << "Valid JSON string import does not emit a false error PASS\n";
}
}
int main(int argc,char** argv) {
  QCoreApplication application(argc,argv);
  taMisc::use_gui=false;
  taMisc::Init_Types();
  try {
    if(argc==2 && String(argv[1])=="string") importString();
    else { vectorTypes(); booleanShapes(); importString(); }
  } catch(const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
  return 0;
}
