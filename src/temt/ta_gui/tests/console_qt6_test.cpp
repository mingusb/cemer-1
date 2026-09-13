// Regression tests use the real console widget, key bindings and CSS interpreter.
#include <iConsole>
#include <iComboBoxPrevNext>
#include <KeyBindings>
#include <KeyBindings_List>
#include <taMisc>
#include <taiMisc>
#include <taSound>
#include <float_Matrix>
#include <Program>
#include <css_qtconsole.h>
#include <css_basic_types.h>

#include <QApplication>
#include <QClipboard>
#include <QInputMethodEvent>
#include <QMimeData>
#include <QSignalSpy>
#include <QScopedValueRollback>
#include <QTemporaryDir>
#include <QTest>
#include <QTimer>
#include <QElapsedTimer>
#include <QScopeGuard>
#ifndef TA_OS_WIN
#include <unistd.h>
#endif
#include <QTextDocument>
#include <iostream>

class ConsoleQt6Test : public QObject {
  Q_OBJECT
private:
  QTemporaryDir preferences;

  static void select(iConsole& console, int start, int end) {
    QTextCursor cursor(console.document());
    cursor.setPosition(start);
    cursor.setPosition(end, QTextCursor::KeepAnchor);
    console.setTextCursor(cursor);
  }

private slots:
  void initTestCase() {
    QVERIFY(preferences.isValid());
    taMisc::use_gui = false; // reflection only; no application windows are required
    taMisc::ext_messages = false;
    taMisc::Init_Types();
    taMisc::ext_messages = false;
    taMisc::prefs_dir = preferences.path();
    taMisc::key_binding_lists = new KeyBindings_List;
    taMisc::key_binding_lists->Add_(new KeyBindings);
    taMisc::key_binding_lists->Add_(new KeyBindings);
    taMisc::current_key_bindings = taMisc::KEY_BINDINGS_DEFAULT;
    taiMisc::LoadDefaultKeyBindings();
  }

  void comboTextSignalsUseQt6Names() {
    taiMisc metrics;
    metrics.InitMetrics();
    QScopedValueRollback<taiMisc*> activeMetrics(taiM_, &metrics);
    iComboBoxPrevNext combo;
    combo.addItems({QStringLiteral("first"), QStringLiteral("second")});
    QSignalSpy changed(&combo, &iComboBoxPrevNext::currentTextChanged);
    QSignalSpy activated(&combo, qOverload<const QString&>(&iComboBoxPrevNext::activated));
    QTest::keyClick(combo.combo_box, Qt::Key_Down);
    QCOMPARE(combo.currentText(), QStringLiteral("second"));
    QCOMPARE(changed.count(), 1);
    QCOMPARE(changed.at(0).at(0).toString(), QStringLiteral("second"));
    QCOMPARE(activated.count(), 1);
    QCOMPARE(activated.at(0).at(0).toString(), QStringLiteral("second"));
    combo.PrevItem();
    QCOMPARE(combo.currentText(), QStringLiteral("first"));
    QCOMPARE(changed.count(), 2);
  }

  void initialPromptAndReset() {
    iConsole console(nullptr, "css> ", false);
    QCOMPARE(console.toPlainText(), QStringLiteral("css> "));
    QCOMPARE(console.getCurrentCommand(), QString());
    console.displayPrompt(true);
    QCOMPARE(console.toPlainText(), QStringLiteral("css> "));
    console.reset();
    QSignalSpy executed(&console, &iConsole::commandExecuted);
    QTest::keyClicks(&console, "command");
    QTest::keyClick(&console, Qt::Key_Return);
    QCOMPARE(executed.count(), 1);
    QCOMPARE(executed.at(0).at(0).toString(), QStringLiteral("command"));
    QCOMPARE(console.toPlainText(), QStringLiteral("css> command\ncss> "));
  }

  void contextPromptKeepsDraft() {
    iConsole console(nullptr, "css> ", false);
    console.replaceCurrentCommand(QStringLiteral("draft"));
    select(console, 7, 7); // after "dr"
    console.setPrompt(QStringLiteral("project<tag>> "));
    QCOMPARE(console.toPlainText(), QStringLiteral("project<tag>> draft"));
    QCOMPARE(console.getCurrentCommand(), QStringLiteral("draft"));
    QCOMPARE(console.textCursor().position(), 16);
  }

  void outputPreservesPromptAndCursor() {
    iConsole console(nullptr, "css> ", false);
    console.replaceCurrentCommand(QStringLiteral("draft"));
    select(console, 7, 7);
    console.outputLine(QStringLiteral("background output"));
    console.outputLine(QStringLiteral("<a href=\"https://example.com/\">help link</a>"));
    QCOMPARE(console.toPlainText(), QStringLiteral("background output\nhelp link\ncss> draft"));
    QCOMPARE(console.getCurrentCommand(), QStringLiteral("draft"));
    QCOMPARE(console.textCursor().position(), console.toPlainText().size() - 3);
    QTextCursor link = console.document()->find(QStringLiteral("help link"));
    QVERIFY(link.charFormat().isAnchor());
    QCOMPARE(link.charFormat().anchorHref(), QStringLiteral("https://example.com/"));
  }

  void promptAndTranscriptAreProtected() {
    iConsole console(nullptr, "css> ", false);
    console.outputLine(QStringLiteral("previous output"));
    const QString transcript = console.toPlainText();
    QTest::keyClick(&console, Qt::Key_Backspace);
    QCOMPARE(console.toPlainText(), transcript);
    select(console, 0, 8);
    QTest::keyClicks(&console, "x");
    QCOMPARE(console.toPlainText(), transcript + QStringLiteral("x"));
    console.selectAll();
    QTest::keyClick(&console, Qt::Key_Backspace);
    QCOMPARE(console.toPlainText(), transcript);
    console.replaceCurrentCommand(QStringLiteral("erase me"));
    console.selectAll();
    QTest::keyClick(&console, Qt::Key_Delete);
    QCOMPARE(console.toPlainText(), transcript);
  }

  void clipboardSlotsProtectTranscript() {
    iConsole console(nullptr, "css> ", false);
    console.outputLine(QStringLiteral("previous output"));
    const QString transcript = console.toPlainText();
    console.replaceCurrentCommand(QStringLiteral("cut me"));
    console.selectAll();
    QVERIFY(QMetaObject::invokeMethod(&console, "cut", Qt::DirectConnection));
    QCOMPARE(console.toPlainText(), transcript);
    QCOMPARE(QApplication::clipboard()->text(), QStringLiteral("cut me"));
    select(console, 0, 8);
    QApplication::clipboard()->setText(QStringLiteral("pasted"));
    QVERIFY(QMetaObject::invokeMethod(&console, "paste", Qt::DirectConnection));
    QCOMPARE(console.toPlainText(), transcript + QStringLiteral("pasted"));
    console.selectAll();
    QApplication::clipboard()->setText(QStringLiteral("replacement"));
    static_cast<QTextEdit*>(&console)->paste(); // inherited API uses protected insertion too
    QCOMPARE(console.toPlainText(), transcript + QStringLiteral("replacement"));
  }

  void multilinePasteIsPlainText() {
    iConsole console(nullptr, "css> ", false);
    auto* mime = new QMimeData;
    mime->setText(QStringLiteral("first\nsecond <b>literal</b>"));
    mime->setHtml(QStringLiteral("<b>not the command</b>"));
    QApplication::clipboard()->setMimeData(mime);
    console.paste();
    QCOMPARE(console.getCurrentCommand(), QStringLiteral("first\nsecond <b>literal</b>"));
    QCOMPARE(console.toPlainText(), QStringLiteral("css> first\nsecond <b>literal</b>"));
  }

  void historyRestoresDraft() {
    iConsole console(nullptr, "css> ", false);
    QStringList history{QStringLiteral("first"), QStringLiteral("second")};
    console.InitHistory(history);
    console.replaceCurrentCommand(QStringLiteral("unfinished"));
    QTest::keyClick(&console, Qt::Key_Up);
    QCOMPARE(console.getCurrentCommand(), QStringLiteral("second"));
    QTest::keyClick(&console, Qt::Key_Up);
    QCOMPARE(console.getCurrentCommand(), QStringLiteral("first"));
    QTest::keyClick(&console, Qt::Key_Down);
    QTest::keyClick(&console, Qt::Key_Down);
    QCOMPARE(console.getCurrentCommand(), QStringLiteral("unfinished"));
    QTest::keyClick(&console, Qt::Key_Down);
    QCOMPARE(console.getCurrentCommand(), QStringLiteral("unfinished"));
    QCOMPARE(console.textCursor().position(), console.toPlainText().size());
  }

  void inputMethodCannotReplacePrompt() {
    iConsole console(nullptr, "css> ", false);
    console.outputLine(QStringLiteral("previous output"));
    const QString transcript = console.toPlainText();
    select(console, 0, 0);
    QInputMethodEvent event;
    event.setCommitString(QString::fromUtf8("λ"), -3, 3);
    QApplication::sendEvent(&console, &event);
    QCOMPARE(console.toPlainText(), transcript + QString::fromUtf8("λ"));
  }

  void keyQueryPreservesDraftAndBackgroundOutput() {
    iConsole console(nullptr, "css> ", false);
    console.replaceCurrentCommand(QStringLiteral("draft"));
    QTimer::singleShot(0, &console, [&console]() {
      console.outputLine(QStringLiteral("background output"));
      QTest::keyClick(&console, Qt::Key_A, Qt::ControlModifier);
    });
    QCOMPARE(console.queryForKeyResponse(QStringLiteral("Press a key")), int(Qt::Key_A));
    QCOMPARE(console.toPlainText(), QStringLiteral("background output\ncss> draft"));
    QCOMPARE(console.getCurrentCommand(), QStringLiteral("draft"));
  }

  void recordsSuccessfulCommands() {
    iConsole console(nullptr, "css> ", false);
    console.execCommand(QStringLiteral("first"));
    console.execCommand(QStringLiteral("second"));
    const QString fileName = preferences.filePath(QStringLiteral("recorded.css"));
    QCOMPARE(console.saveScript(fileName), 0);
    QFile file(fileName);
    QVERIFY(file.open(QIODevice::ReadOnly));
    QCOMPARE(file.readAll(), QByteArray("first\nsecond\n"));
    console.reset();
    QCOMPARE(console.loadScript(fileName), 0);
    QCOMPARE(console.toPlainText(), QStringLiteral("css> first\ncss> second\ncss> "));
    QCOMPARE(console.getCurrentCommand(), QString());
  }

#ifndef TA_OS_WIN
  void repeatedStdoutAndStderrDelivery() {
    QScopedValueRollback<bool> messages(taMisc::ext_messages, true);
    QString transcript;
    QString command;
    {
      iConsole console(nullptr, "css> ", true);
      console.replaceCurrentCommand(QStringLiteral("draft"));
      std::cout << "first output" << std::endl;
      console.flushOutput();
      std::cout << "second output" << std::endl;
      std::cerr << "error output" << std::endl;
      console.flushOutput();
      transcript = console.toPlainText();
      command = console.getCurrentCommand();
    }
    QCOMPARE(transcript, QStringLiteral("first output\nsecond output\nerror output\ncss> draft"));
    QCOMPARE(command, QStringLiteral("draft"));
  }
#endif

  void pcm32StereoRoundTripAndChannelSelection() {
    float_Matrix input;
    input.SetGeom(2, 2, 3);
    const float samples[] = {-1.0f, 0.75f, -0.5f, 0.5f, 0.0f, 1.0f};
    for(int index = 0; index < 6; ++index)
      input.FastEl_Flat(index) = samples[index];
    taSound sound;
    QVERIFY(sound.SoundFromMatrix(input, -1, 48000, 32, taSound::SignedInt));
    QCOMPARE(sound.FrameCount(), 3);
    QCOMPARE(sound.ChannelCount(), 2);
    QCOMPARE(sound.ByteCount(), 24);
    float_Matrix output;
    QVERIFY(sound.SoundToMatrix(output));
    for(int index = 0; index < 6; ++index)
      QVERIFY(qAbs(output.FastEl_Flat(index) - samples[index]) < 0.00001f);
    QVERIFY(sound.SoundFromMatrix(input, 1, 48000, 32, taSound::SignedInt));
    QCOMPARE(sound.ChannelCount(), 1);
    for(int frame = 0; frame < 3; ++frame)
      QVERIFY(qAbs(sound.GetSample_frame(frame) - samples[frame * 2 + 1]) < 0.00001f);
  }

  void unsignedPcmIsCenteredOnSilence() {
    float_Matrix input;
    input.SetGeom(1, 3);
    input.FastEl_Flat(0) = -1.0f;
    input.FastEl_Flat(1) = 0.0f;
    input.FastEl_Flat(2) = 1.0f;
    taSound sound;
    QVERIFY(sound.SoundFromMatrix(input, -1, 48000, 8, taSound::UnSignedInt));
    const auto* bytes = static_cast<const unsigned char*>(sound.SoundData());
    QCOMPARE(bytes[0], static_cast<unsigned char>(0));
    QCOMPARE(bytes[1], static_cast<unsigned char>(128));
    QCOMPARE(bytes[2], static_cast<unsigned char>(255));
    QCOMPARE(sound.GetSample_frame(0), -1.0f);
    QCOMPARE(sound.GetSample_frame(1), 0.0f);
    QCOMPARE(sound.GetSample_frame(2), 1.0f);
  }

  void emptyCssArrayDoesNotOwnVoid() {
    const int references = cssMisc::Void.refn;
    {
      cssArray empty(0);
    }
    QCOMPARE(cssMisc::Void.refn, references);
  }

  void realCssInterpreterArithmetic() {
    QVERIFY(cssMisc::Initialize());
    const auto shutdownCss = qScopeGuard([]() { cssMisc::Shutdown(); });
    cssMisc::TopShell->PushSrcProg(cssMisc::Top);
    auto* result = new cssInt(0, "qt_console_result");
    cssMisc::HardVars.Push(result);
    {
      QcssConsole console(nullptr, cssMisc::TopShell);
      console.execCommand(QStringLiteral("qt_console_result = 6 * 7;"));
      QCOMPARE(static_cast<int>(*result), 42);
      QCOMPARE(console.getCurrentCommand(), QString());
      QVERIFY(console.toPlainText().endsWith(QStringLiteral("css> ")));
      console.replaceCurrentCommand(QStringLiteral("qt_console_res"));
      QTest::keyClick(&console, Qt::Key_Tab);
      QCOMPARE(console.getCurrentCommand(), QStringLiteral("qt_console_result"));
      console.execCommand(QStringLiteral("qt_console_result = ;"));
      QVERIFY(!cssMisc::last_err_msg.empty());
      console.execCommand(QStringLiteral("qt_console_result = 7 * 8;"));
      QCOMPARE(static_cast<int>(*result), 56);
      QVERIFY(cssMisc::last_err_msg.empty());
      const QString recorded = preferences.filePath(QStringLiteral("css-recovery.css"));
      QCOMPARE(console.saveScript(recorded), 0);
      QFile file(recorded);
      QVERIFY(file.open(QIODevice::ReadOnly));
      QVERIFY(!file.readAll().contains("qt_console_result = ;"));
      {
        QScopedValueRollback<bool> gui(taMisc::gui_active, true);
        QScopedValueRollback<bool> loop(taMisc::in_event_loop, true);
        QScopedValueRollback<bool> stop(Program::stop_req, false);
        QScopedValueRollback<int> interval(taMisc::css_gui_event_interval, 10);
        bool interrupted = false;
        QTimer timer;
        timer.setSingleShot(true);
        connect(&timer, &QTimer::timeout, &console, [&]() {
          interrupted = true;
          const QString submitted = console.toPlainText();
          QApplication::clipboard()->setText(QStringLiteral("unexpected input"));
          console.paste();
          QInputMethodEvent input;
          input.setCommitString(QStringLiteral("unexpected input"));
          QApplication::sendEvent(&console, &input);
          const QString afterInput = console.toPlainText();
          QTest::keyClick(&console, Qt::Key_C, Qt::ControlModifier);
          QCOMPARE(afterInput, submitted);
        });
        timer.start(50);
        QElapsedTimer elapsed;
        elapsed.start();
        console.execCommand(QStringLiteral("while(qt_console_result < 100000000) { qt_console_result += 1; }"));
        QVERIFY(interrupted);
        QVERIFY(elapsed.elapsed() < 10000);
        QVERIFY(static_cast<int>(*result) < 100000000);
        QVERIFY(console.toPlainText().contains(QStringLiteral("while(qt_console_result")));
        QCOMPARE(console.getCurrentCommand(), QString());
      }
      console.execCommand(QStringLiteral("qt_console_result = 9 * 9;"));
      QCOMPARE(static_cast<int>(*result), 81);
    }
#ifndef TA_OS_WIN
    {
      int pipeFds[2];
      QVERIFY(::pipe(pipeFds) == 0);
      const int savedInput = ::dup(STDIN_FILENO);
      QVERIFY(savedInput >= 0);
      const auto restoreInput = qScopeGuard([&]() {
        ::dup2(savedInput, STDIN_FILENO);
        ::close(savedInput);
        ::close(pipeFds[0]);
        ::close(pipeFds[1]);
      });
      QVERIFY(::dup2(pipeFds[0], STDIN_FILENO) >= 0);
      QScopedValueRollback<bool> externalExit(cssMisc::TopShell->external_exit, false);
      bool servicedTimer = false;
      QTimer timer;
      timer.setSingleShot(true);
      connect(&timer, &QTimer::timeout, this, [&]() {
        servicedTimer = true;
        cssMisc::TopShell->external_exit = true;
      });
      timer.start(50);
      QElapsedTimer elapsed;
      elapsed.start();
      cssMisc::TopShell->Shell_NoConsole_Run();
      QVERIFY(servicedTimer);
      QVERIFY(elapsed.elapsed() < 10000);
    }
#endif
  }
};

QTEST_MAIN(ConsoleQt6Test)
#include "console_qt6_test.moc"
