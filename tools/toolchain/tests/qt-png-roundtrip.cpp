// CPU-only PNG ABI regression for the selected Qt and native image libraries.
#include <QBuffer>
#include <QCoreApplication>
#include <QFile>
#include <QImage>
#include <QImageReader>
#include <QImageWriter>
#include <QTemporaryDir>
#include <iostream>
#include <stdexcept>

static void require(bool condition, const QString& message) {
  if (!condition) throw std::runtime_error(message.toStdString());
}

static void checkPixels(const QImage& actual, const QImage& expected) {
  require(actual.size() == expected.size(), "PNG dimensions changed");
  for (int y = 0; y < expected.height(); ++y)
    for (int x = 0; x < expected.width(); ++x)
      require(actual.pixelColor(x, y).rgba64() == expected.pixelColor(x, y).rgba64(),
              QString("PNG sample changed at (%1, %2)").arg(x).arg(y));
}

int main(int argc, char **argv) {
  QCoreApplication application(argc, argv);
  try {
    QTemporaryDir directory;
    require(directory.isValid(), "Could not create PNG test directory");
    require(QImageReader::supportedImageFormats().contains("png"), "PNG reader missing");
    require(QImageWriter::supportedImageFormats().contains("png"), "PNG writer missing");
    const QImage::Format formats[] = {QImage::Format_ARGB32, QImage::Format_RGBA64,
                                    QImage::Format_Grayscale16, QImage::Format_Indexed8};
    for (QImage::Format format : formats) {
      QImage original(17, 13, format);
      if (format == QImage::Format_Indexed8)
        original.setColorTable({qRgba(0, 0, 0, 0), qRgba(255, 0, 0, 255),
                                qRgba(0, 255, 0, 127), qRgba(0, 0, 255, 255)});
      for (int y = 0; y < original.height(); ++y) {
        for (int x = 0; x < original.width(); ++x) {
          const auto sample = static_cast<quint16>((x * 3457 + y * 5311) & 65535);
          if (format == QImage::Format_Grayscale16)
            reinterpret_cast<quint16 *>(original.scanLine(y))[x] = sample;
          else if (format == QImage::Format_Indexed8)
            original.setPixel(x, y, static_cast<uint>((x + y) % 4));
          else
            original.setPixelColor(x, y, QColor::fromRgba64(
              sample, static_cast<quint16>(65535 - sample),
              static_cast<quint16>((sample * 7) & 65535),
              static_cast<quint16>(x % 3 == 0 ? 0 : x % 3 == 1 ? 32768 : 65535)));
        }
      }
      QByteArray encoded;
      QBuffer output(&encoded);
      require(output.open(QIODevice::WriteOnly), "Could not open PNG buffer");
      QImageWriter writer(&output, "png");
      require(writer.write(original), writer.errorString());
      require(encoded.startsWith(QByteArray::fromHex("89504e470d0a1a0a")), "PNG signature missing");
      QImage decoded = QImage::fromData(encoded, "png");
      require(!decoded.isNull(), "Could not decode PNG buffer");
      checkPixels(decoded, original);
      const QString path = directory.filePath(QString("format-%1.png").arg(format));
      require(original.save(path, "PNG"), "Could not save PNG file");
      QImageReader reader(path, "png");
      QImage fromFile = reader.read();
      require(!fromFile.isNull(), reader.errorString());
      checkPixels(fromFile, original);
      std::cout << "PASS format " << format << ": " << encoded.size()
                << " PNG bytes; memory and file pixels match\n";
    }
    QFile maps("/proc/self/maps");
    require(maps.open(QIODevice::ReadOnly), "Could not inspect loaded libraries");
    const QByteArray loaded = maps.readAll();
    require(loaded.contains("libpng18.so"), "Selected FreeType PNG18 dependency missing");
    require(!loaded.contains("libpng16.so"), "Unexpected host PNG16 library loaded");
    std::cout << "PASS Qt PNG codec coexists with selected FreeType/PNG18\n";
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
  return 0;
}
