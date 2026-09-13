#include <Quarter/Quarter.h>
#include <Quarter/QuarterWidget.h>
#include <Quarter/Mouse.h>
#include <Quarter/QtCoinCompatibility.h>
#include <Inventor/SbImage.h>
#include <Inventor/events/SoMouseButtonEvent.h>
#include <Inventor/nodes/SoSeparator.h>
#include <Inventor/nodes/SoCube.h>
#include <Inventor/nodes/SoMaterial.h>
#include <Inventor/nodes/SoRotationXYZ.h>
#include <QAction>
#include <QOpenGLContext>
#include <QOpenGLFunctions>
#include <QTest>
#include <QWheelEvent>

using namespace SIM::Coin3D::Quarter;

class QuarterQt6Test : public QObject {
  Q_OBJECT
private slots:
  void initTestCase() { Quarter::init(); }
  void cleanupTestCase() { Quarter::clean(); }

  void imageConversion() {
    // RGB888 rows have padding, and modern Qt loaders need not return RGB32.
    QImage original(3, 2, QImage::Format_RGB888);
    original.fill(Qt::red);
    original.setPixelColor(2, 0, Qt::blue);
    original.setPixelColor(0, 1, Qt::green);
    SbImage coin;
    QtCoinCompatibility::QImageToSbImage(original, coin);
    QImage restored;
    QtCoinCompatibility::SbImageToQImage(coin, restored);
    QCOMPARE(restored.size(), original.size());
    for (int y = 0; y < original.height(); ++y)
      for (int x = 0; x < original.width(); ++x)
        QCOMPARE(restored.pixelColor(x, y), original.pixelColor(x, y));

    QImage alpha(3, 2, QImage::Format_ARGB32_Premultiplied);
    alpha.fill(QColor(255, 0, 0, 128));
    QtCoinCompatibility::QImageToSbImage(alpha, coin);
    QtCoinCompatibility::SbImageToQImage(coin, restored);
    QCOMPARE(restored.pixelColor(1, 1), QColor(255, 0, 0, 128));

    const unsigned char grayalpha[] = {80, 120};
    coin.setValue(SbVec2s(1, 1), 2, grayalpha);
    QtCoinCompatibility::SbImageToQImage(coin, restored);
    QCOMPARE(restored.pixelColor(0, 0), QColor(80, 80, 80, 120));

    QtCoinCompatibility::QImageToSbImage(QImage(), coin);
    QtCoinCompatibility::SbImageToQImage(coin, restored);
    QVERIFY(restored.isNull());
  }

  void wheelEvents() {
    QuarterWidget widget;
    Mouse mouse(&widget);
    QWheelEvent begin(QPointF(20, 20), QPointF(20, 20), QPoint(), QPoint(),
                      Qt::NoButton, Qt::NoModifier, Qt::ScrollBegin, false);
    QVERIFY(mouse.translateEvent(&begin) == nullptr);
    QWheelEvent up(QPointF(20, 20), QPointF(20, 20), QPoint(), QPoint(0, 120),
                   Qt::NoButton, Qt::NoModifier, Qt::ScrollUpdate, false);
    const auto *event = static_cast<const SoMouseButtonEvent *>(mouse.translateEvent(&up));
    QVERIFY(event);
    QCOMPARE(event->getButton(), SoMouseButtonEvent::BUTTON4);
    QWheelEvent down(QPointF(20, 20), QPointF(20, 20), QPoint(0, -4), QPoint(),
                     Qt::NoButton, Qt::NoModifier, Qt::ScrollUpdate, false);
    event = static_cast<const SoMouseButtonEvent *>(mouse.translateEvent(&down));
    QVERIFY(event);
    QCOMPARE(event->getButton(), SoMouseButtonEvent::BUTTON5);
  }

  void renderAndReparent() {
    QWidget first;
    QWidget second;
    first.resize(360, 300);
    second.resize(360, 300);
    QuarterWidget widget(&first);
    widget.resize(320, 240);
    widget.setBackgroundColor(Qt::black);
    widget.setNavigationModeFile();
    auto *scene = new SoSeparator;
    auto *material = new SoMaterial;
    material->diffuseColor.setValue(1.0f, 0.0f, 0.0f);
    scene->addChild(material);
    auto *rotatex = new SoRotationXYZ;
    rotatex->axis = SoRotationXYZ::X;
    rotatex->angle = 0.35f;
    scene->addChild(rotatex);
    auto *rotatey = new SoRotationXYZ;
    rotatey->axis = SoRotationXYZ::Y;
    rotatey->angle = 0.55f;
    scene->addChild(rotatey);
    scene->addChild(new SoCube);
    widget.setSceneGraph(scene);
    first.show();
    QVERIFY(QTest::qWaitForWindowExposed(&first));
    QTRY_VERIFY(widget.isValid());
    widget.viewAll();
    QTest::qWait(100);
    auto verifyFrame = [&widget]() {
      const QImage frame = widget.grabFramebuffer();
      QVERIFY(!frame.isNull());
      QCOMPARE(frame.size(), QSize(qRound(widget.width() * widget.devicePixelRatioF()),
                                   qRound(widget.height() * widget.devicePixelRatioF())));
      int redpixels = 0;
      for (int y = 0; y < frame.height(); ++y)
        for (int x = 0; x < frame.width(); ++x) {
          const QColor color = frame.pixelColor(x, y);
          if (color.red() > 40 && color.red() > 2 * color.green()) ++redpixels;
        }
      QVERIFY2(redpixels > 200, "Coin scene did not appear in Qt's framebuffer");
      QVERIFY(frame.save("quarter-qt6-render.png"));
    };
    verifyFrame();
    const uint32_t oldcache = widget.getCacheContextId();
    widget.setParent(&second);
    second.show();
    widget.show();
    QVERIFY(QTest::qWaitForWindowExposed(&second));
    QTRY_VERIFY(widget.isValid());
    QVERIFY(widget.getCacheContextId() != oldcache);
    verifyFrame();
    QVERIFY(widget.getContextMenu());
    for (QAction *action : widget.renderModeActions()) {
      action->trigger();
      QCOMPARE(int(widget.renderMode()), action->data().toInt());
      QVERIFY(!widget.grabFramebuffer().isNull());
      widget.makeCurrent();
      QCOMPARE(widget.context()->functions()->glGetError(), GLenum(GL_NO_ERROR));
      widget.doneCurrent();
    }
    widget.setRenderMode(QuarterWidget::AS_IS);
    verifyFrame();
  }
};

QTEST_MAIN(QuarterQt6Test)
#include "quarter_qt6_test.moc"
