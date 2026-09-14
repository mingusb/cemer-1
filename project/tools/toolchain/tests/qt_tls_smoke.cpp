#include <QCoreApplication>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QSslSocket>
#include <QTimer>
#include <QUrl>
#include <cstdio>

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  const auto runtime = QSslSocket::sslLibraryVersionString();
  std::printf("Qt %s; TLS build %s; TLS runtime %s\n", qVersion(),
              qPrintable(QSslSocket::sslLibraryBuildVersionString()), qPrintable(runtime));
  if (!QSslSocket::supportsSsl() || !runtime.startsWith("OpenSSL 3."))
    return 2;
  QNetworkAccessManager manager;
  auto* reply = manager.get(QNetworkRequest(QUrl(QStringLiteral("https://www.qt.io/"))));
  QObject::connect(reply, &QNetworkReply::finished, &app, [&] {
    const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
    const QByteArray body = reply->readAll();
    std::printf("HTTPS status %d; bytes %lld; network_error %d\n", status,
                static_cast<long long>(body.size()), static_cast<int>(reply->error()));
    app.exit(reply->error() == QNetworkReply::NoError && status == 200 && !body.isEmpty() ? 0 : 3);
  });
  QTimer::singleShot(30000, &app, [&] { app.exit(4); });
  return app.exec();
}
