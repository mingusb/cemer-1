#include <Quarter/QtCoinCompatibility.h>
#include <Inventor/SbImage.h>
#include <QImage>
#include <cstring>
#include <limits>

using namespace SIM::Coin3D::Quarter;

void
QtCoinCompatibility::QImageToSbImage(const QImage & image, SbImage & sbimage)
{
  // Coin uses signed-short dimensions and bottom-to-top rows. Normalize Qt
  // image formats before accessing bytes and honor each row's padding.
  if (image.isNull() || image.width() > std::numeric_limits<short>::max() ||
      image.height() > std::numeric_limits<short>::max()) {
    sbimage.setValue(SbVec2s(0, 0), 0, nullptr);
    return;
  }
  const bool grayscale = image.isGrayscale() && !image.hasAlphaChannel();
  const int components = grayscale ? 1 : (image.hasAlphaChannel() ? 4 : 3);
  const QImage normalized = image.convertToFormat(grayscale
    ? QImage::Format_Grayscale8 : QImage::Format_RGBA8888);
  SbVec2s size(image.width(), image.height());
  sbimage.setValue(size, components, nullptr);
  int storedcomponents;
  unsigned char *buffer = sbimage.getValue(size, storedcomponents);

  for (int y = 0; y < image.height(); ++y) {
    const unsigned char *source = normalized.constScanLine(image.height() - y - 1);
    unsigned char *destination = buffer + y * image.width() * components;
    if (components == 1 || components == 4) {
      std::memcpy(destination, source, image.width() * components);
    } else {
      for (int x = 0; x < image.width(); ++x) {
        std::memcpy(destination + x * 3, source + x * 4, 3);
      }
    }
  }
}

void
QtCoinCompatibility::SbImageToQImage(const SbImage & sbimage, QImage & image)
{
  SbVec2s size;
  int components;
  const unsigned char *source = sbimage.getValue(size, components);
  if (!source || components < 1 || components > 4) {
    image = QImage();
    return;
  }
  image = QImage(size[0], size[1], components == 1
    ? QImage::Format_Grayscale8 : QImage::Format_RGBA8888);
  if (image.isNull()) return;

  for (int y = 0; y < size[1]; ++y) {
    unsigned char *destination = image.scanLine(size[1] - y - 1);
    if (components == 1) {
      std::memcpy(destination, source, size[0]);
      source += size[0];
      continue;
    }
    for (int x = 0; x < size[0]; ++x) {
      if (components == 2) {
        destination[0] = destination[1] = destination[2] = *source++;
        destination[3] = *source++;
      } else {
        destination[0] = *source++;
        destination[1] = *source++;
        destination[2] = *source++;
        destination[3] = components == 4 ? *source++ : 255;
      }
      destination += 4;
    }
  }
}
