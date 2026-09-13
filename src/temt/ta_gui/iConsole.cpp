
// C2018ight 2013-2017, Regents of the University of Colorado,
// Carnegie Mellon University, Princeton University.
//
// This file is part of The Emergent Toolkit
//
//   This library is free software; you can redistribute it and/or
//   modify it under the terms of the GNU Lesser General Public
//   License as published by the Free Software Foundation; either
//   version 2.1 of the License, or (at your option) any later version.
//
//   This library is distributed in the hope that it will be useful,
//   but WITHOUT ANY WARRANTY; without even the implied warranty of
//   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
//   Lesser General Public License for more details.

#include "iConsole.h"

/***************************************************************************
                          qconsole.cpp  -  description
                             -------------------
    begin                : mar mar 15 2005
    copyright            : (C) 2005 by Houssem BDIOUI and Randall C. O'Reilly
    email                : houssem.bdioui@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/

#include <taMisc>
#include <taiMisc> // for taiMisc::KeyEventCtrlPressed(e)

#include <qfile.h>

#include <QMouseEvent>
#include <QTextStream>
#include <QKeyEvent>
#include <QTextCursor>
#include <QApplication>
#include <QCoreApplication>
#include <QDir>
#include <QMenu>
#include <QScrollBar>
#include <QMimeData>
#include <QTextDocumentFragment>
#include <QClipboard>
#include <QDesktopServices>
#include <QInputMethodEvent>
#include <QDropEvent>
#include <QTextDocument>

//#include <QDebug>

#include <iostream>


// buried in qtextcontrol_p.h
class MyQTextEditMimeData : public QMimeData
{
public:
    inline MyQTextEditMimeData(const QTextDocumentFragment &aFragment) : fragment(aFragment) {}

    QStringList formats() const override;
protected:
    QVariant retrieveData(const QString &mimeType, QMetaType type) const override;
private:
    void setup() const;

    mutable QTextDocumentFragment fragment;
};

QStringList MyQTextEditMimeData::formats() const
{
    if (!fragment.isEmpty())
        return QStringList() << QString::fromLatin1("text/plain") << QString::fromLatin1("text/html")
        ;
    else
        return QMimeData::formats();
}

QVariant MyQTextEditMimeData::retrieveData(const QString &mimeType, QMetaType type) const
{
    if (!fragment.isEmpty())
        setup();
    return QMimeData::retrieveData(mimeType, type);
}

void MyQTextEditMimeData::setup() const
{
    MyQTextEditMimeData *that = const_cast<MyQTextEditMimeData *>(this);
    that->setData(QLatin1String("text/html"), fragment.toHtml().toUtf8());
    that->setText(fragment.toPlainText());
    fragment = QTextDocumentFragment();
}


using namespace std;

void iConsole::InitHistory(QStringList& string_list) {
  int max_commands = 100;
  // keep the saved list to around 100 by reducing it to 100 on startup
  if (string_list.length() > max_commands) {
    String filename = taMisc::prefs_dir + PATH_SEP + "console_history";
    QFile history_file(filename);
    if (history_file.open(QIODevice::Truncate | QIODevice::WriteOnly)) {
      QTextStream out(&history_file);
      int start = string_list.length() - max_commands;
      for (int i=start; i<string_list.length(); i++) {
        QString command = string_list[i];
        out << command << Qt::endl;
      }
      history_file.close();
    }
  }
  
  // load the saved command strings
  for (int i=0; i<string_list.length(); i++) {
    QString command = string_list[i];
    history.append(command);
  }
  historyIndex = history.size();
}

void iConsole::setFontNameSize(QString fnm, int sz) {
  setFontFamily(fnm);
  setFontPointSize(sz);
  QFont font(fnm, sz);          // this latter seems to be the thing that actually works..
  setFont(font);
}

void iConsole::setFont(const QFont& font) {
  setCurrentFont(font);
  document()->setDefaultFont(font);
  getDisplayGeom();
}

void iConsole::setPager(bool pager) {
  noPager = !pager;
}

void iConsole::getDisplayGeom() {
  QFontMetrics fm(currentFont());
  fontHeight = fm.height();
  fontWidth = fm.horizontalAdvance("m");
  if(fontHeight < 5) fontHeight = 5;
  if(fontWidth < 5) fontWidth = 5;
  maxLines = (height() / fontHeight) - 4;
  maxCols = (width() / fontWidth) - 1;
  if(maxLines < 10) maxLines = 10;
  if(maxCols < 10) maxCols = 10;
}

//Clear the console
void iConsole::clear() {
  setFontNameSize(taMisc::font_names.console, taMisc::GetCurrentFontSize("console"));
  inherited::clear();
  promptDisp = false;
  historyIndex = history.size();
  historyDraft.clear();
  setFontNameSize(taMisc::font_names.console, taMisc::GetCurrentFontSize("console"));
  ext_select_on = false;
  getDisplayGeom();
  curPromptPos = 0;
  curOutputLn = 0;
  quitPager = false;
  contPager = false;
  waiting_for_key = false;
  key_response = 0;
  setAcceptRichText(false);     // pasted commands are always plain text
  setUndoRedoEnabled(false);    // document undo must never remove submitted output or prompts
  setReadOnly(false);           // this determines if links are clickable
  setOpenExternalLinks(false);
  setOpenLinks(false);          // we do it ourselves b/c it doesn't seem to work otherwise

  displayPrompt(true);          // force
}

//Reset the console
void iConsole::reset() {
  historyIndex = 0;
  history.clear();
  recordedScript.clear();
  historyDraft.clear();
  clear();
}

void iConsole::exit() {
  qApp->exit();
}

void iConsole::onQuit() {
  applicationIsQuitting = true;
}

//iConsole constructor (init the QTextEdit & the attributes)
iConsole::iConsole(QWidget *parent, const char *name, bool initiInterceptor)
  : inherited(parent)
  , cmdColor(Qt::blue)
  , errColor(Qt::red)
  , outColor(Qt::black)
  , completionColor(Qt::darkGreen)
  , curPromptPos(0), curOutputLn(0), maxLines(10), maxCols(10)
  , fontHeight(0), fontWidth(0)
  , applicationIsQuitting(false)
  , noPager(true), quitPager(false), contPager(false)
  , executingCommand(false), promptDisp(false), waiting_for_key(false)
  , key_response(0), promptLength(0)
  , prompt(name && *name ? QString::fromUtf8(name) : QStringLiteral("> "))
  , historyIndex(0), ext_select_on(false)
#ifndef TA_OS_WIN
  , stdoutiInterceptor(NULL), stderriInterceptor(NULL)
#endif
{
  outColor = palette().color(QPalette::Text);
  if(palette().color(QPalette::Base).lightness() < 128) {
    cmdColor = QColor(100, 180, 255);
    errColor = QColor(255, 110, 110);
    completionColor = QColor(120, 220, 150);
  }
  //resets the console
  reset();

  connect(this, SIGNAL(anchorClicked(const QUrl&)), SLOT(linkClicked(const QUrl&)));

#ifndef TA_OS_WIN
  if(initiInterceptor && taMisc::ext_messages) {
    //Initialize the interceptors
    stdoutiInterceptor = new iInterceptor(this);
    stdoutiInterceptor->initialize(1);
    connect(stdoutiInterceptor, SIGNAL(received(QTextStream *)), SLOT(stdReceived()));

    stderriInterceptor = new iInterceptor(this);
    stderriInterceptor->initialize(2);
    connect(stderriInterceptor, SIGNAL(received(QTextStream *)), SLOT(stdReceived()));
  }
#endif
}

//Sets the prompt and cache the prompt length to optimize the processing speed
void iConsole::setPrompt(QString newPrompt, bool display) {
  prompt = newPrompt.isEmpty() ? QStringLiteral("> ") : newPrompt;
  if(!display || executingCommand)
    return;
  if(promptDisp) {
    // Change the shell context without losing a partially typed command.
    QTextCursor savedCursor = textCursor();
    QTextCursor cursor(document());
    cursor.setPosition(curPromptPos - promptLength);
    cursor.setPosition(curPromptPos, QTextCursor::KeepAnchor);
    QTextCharFormat format;
    format.setForeground(cmdColor);
    cursor.insertText(prompt, format);
    curPromptPos = cursor.position();
    promptLength = prompt.length();
    setTextCursor(savedCursor);
  }
  else {
    displayPrompt();
  }
}

void iConsole::flushOutput() {
  cout.flush();
  cerr.flush();
#ifndef TA_OS_WIN
  bool waiting = false;
  do {
    if(stdoutiInterceptor) {
      waiting = stdDisplay(stdoutiInterceptor->textIStream());
    }
    if(stderriInterceptor) {
      waiting = (stdDisplay(stderriInterceptor->textIStream(), true) || waiting);
    }
    if(waiting) {
      // doing any kind of pending / process events here is bad -- causes hangs!
      // taMisc::RunPending();
      // QCoreApplication::processEvents();
      // taMisc::SleepMs(1); //note: 1ms is fine, shorter values result in cpu thrashing
    }
  } while(waiting);
#endif
}

int iConsole::queryForKeyResponse(QString query) {
  flushOutput();
  const int queryStart = promptDisp ? curPromptPos - promptLength
                                    : document()->characterCount() - 1;
  appendOutput(query, cmdColor);
  const int queryEnd = promptDisp ? curPromptPos - promptLength
                                  : document()->characterCount() - 1;
  QTextCursor queryCursor(document());
  queryCursor.setPosition(queryStart);
  queryCursor.setPosition(queryEnd, QTextCursor::KeepAnchor);
  queryCursor.setKeepPositionOnInsert(true);
  waiting_for_key = true;
  key_response = 0;
  while(waiting_for_key && !applicationIsQuitting) {
    QCoreApplication::processEvents();
    taMisc::SleepMs(10);
  }
  // Remove only the temporary question, preserving output received while waiting.
  if(promptDisp && curPromptPos >= queryCursor.selectionEnd())
    curPromptPos -= queryCursor.selectionEnd() - queryCursor.selectionStart();
  queryCursor.removeSelectedText();
  return key_response;
}

void iConsole::stdReceived() {
  flushOutput();
}

// Displays the prompt and move the cursor to the end of the line.
void iConsole::displayPrompt(bool force) {
  flushOutput();
  if(promptDisp) {
    if(force) {
      ensureCursorVisible();
      repaint();
    }
    return;
  }
  QTextCursor cursor(document());
  cursor.movePosition(QTextCursor::End);
  if(!document()->isEmpty())
    cursor.insertBlock();
  QTextCharFormat format;
  format.setForeground(cmdColor);
  cursor.insertText(prompt, format);
  setTextCursor(cursor);
  curPromptPos = cursor.position();
  promptLength = prompt.length();
  quitPager = false;
  contPager = false;
  promptDisp = true;
  ensureCursorVisible();
  repaint();
}

void iConsole::gotoPrompt(QTextCursor& cursor, bool select) {
  if(select)
    cursor.setPosition(curPromptPos, QTextCursor::KeepAnchor);
  else 
    cursor.setPosition(curPromptPos, QTextCursor::MoveAnchor);
}

void iConsole::gotoEnd(QTextCursor& cursor, bool select) {
  if(select)
    cursor.movePosition(QTextCursor::End, QTextCursor::KeepAnchor); // selects
  else
    cursor.movePosition(QTextCursor::End, QTextCursor::MoveAnchor); // not selects
}

void iConsole::gotoEnd() {
  QTextCursor cursor(textCursor());
  gotoEnd(cursor, false);
  setTextCursor(cursor);
}

bool iConsole::scrolledToEnd() {
  // check if scrollbar is scrolled to end
  QScrollBar* vscr = verticalScrollBar();
  if(!vscr) return true;
  return (vscr->value() >= vscr->maximum() - 4); // give a few lines at the end leeway
}

void iConsole::appendOutput(const QString& line, const QColor& color) {
  const bool atEnd = scrolledToEnd();
  const bool editing = promptDisp;
  QTextCursor savedCursor = textCursor();
  const int commandPosition = curPromptPos;
  const int cursorOffset = savedCursor.position() - commandPosition;
  const int anchorOffset = savedCursor.anchor() - commandPosition;
  const QString command = editing ? getCurrentCommand() : QString();
  QTextCursor cursor(document());
  if(editing) {
    // Background output belongs above the live prompt, so it cannot consume input.
    cursor.setPosition(curPromptPos - promptLength);
    cursor.movePosition(QTextCursor::End, QTextCursor::KeepAnchor);
    cursor.removeSelectedText();
  }
  else {
    cursor.movePosition(QTextCursor::End);
    if(!document()->isEmpty())
      cursor.insertBlock();
  }
  QTextCharFormat format;
  format.setForeground(color);
  cursor.setCharFormat(format);
  if(Qt::mightBeRichText(line))
    cursor.insertHtml(line);
  else
    cursor.insertText(line);
  if(editing) {
    cursor.insertBlock();
    format.setForeground(cmdColor);
    cursor.insertText(prompt, format);
    curPromptPos = cursor.position();
    promptLength = prompt.length();
    cursor.insertText(command, format);
    cursor.setPosition(anchorOffset >= 0 ? curPromptPos + anchorOffset : savedCursor.anchor());
    cursor.setPosition(cursorOffset >= 0 ? curPromptPos + cursorOffset : savedCursor.position(),
                       QTextCursor::KeepAnchor);
    setTextCursor(cursor);
  }
  else if(atEnd) {
    setTextCursor(cursor);
  }
  if(atEnd)
    ensureCursorVisible();
  viewport()->update();
}

void iConsole::outputLine(QString line, bool err) {
  appendOutput(line, err ? errColor : outColor);
}

#ifndef TA_OS_WIN
// displays redirected stdout/stderr
bool iConsole::stdDisplay(QTextStream* s, bool err) {
  // always grab output!  no paging at all ever on std out -- need to get it!
  bool scrolled_to_end = scrolledToEnd();
  int n_lines_recvd = 0;
  // no pager mode just grabs everything and returns true if any lines were recv'd
  while(true) {
    QString line = s->readLine();
    if(line.isNull()) break;
    n_lines_recvd++;
    if(taMisc::ext_messages) {
      appendOutput(line, err ? errColor : outColor);
    }
    taMisc::LogEvent(line);
    if(logfile.isOpen()) {
      logfile.write(line.toLocal8Bit());
      logfile.write("\n", strlen("\n"));
      logfile.flush();
    }
  }

  if(scrolled_to_end && !promptDisp) {
    gotoEnd();
  }
  if(n_lines_recvd > 0)
    emit receivedNewStdin(n_lines_recvd);
  return (n_lines_recvd > 0);
}
#endif

void iConsole::resizeEvent(QResizeEvent* e) {
  getDisplayGeom();
  inherited::resizeEvent(e);
}

// Reimplemented key press event
void iConsole::keyPressEvent(QKeyEvent* key_event)
{
  if(waiting_for_key) {
    if(key_event->key() == Qt::Key_Control || key_event->key() == Qt::Key_Shift ||
       key_event->key() == Qt::Key_Alt || key_event->key() == Qt::Key_Meta) {
      key_event->accept();
      return;
    }
    key_response = key_event->key();
    waiting_for_key = false;
    key_event->accept();
    return;
  }
  taiMisc::BoundAction action = taiMisc::GetActionFromKeyEvent(taiMisc::CONSOLE_CONTEXT, key_event);
  if(executingCommand) {
    if(action == taiMisc::CONSOLE_UNDO || action == taiMisc::CONSOLE_UNDO_II)
      ctrlCPressed();
    key_event->accept();
    return;
  }

  if (curOutputLn >= maxLines) {
    if (key_event->key() == Qt::Key_Return || key_event->key() == Qt::Key_Enter) {
      curOutputLn = 0;
    }
    else if (action == taiMisc::CONSOLE_QUIT_PAGING) {
      curOutputLn = 0;
      quitPager = true;
    }
    else if (action == taiMisc::CONSOLE_CONTINUE_PAGING) {
      curOutputLn = 0;
      contPager = true;
    }
    flushOutput();
    promptDisp = false;
    key_event->accept();
    return;
  }
  
  QTextCursor cursor(textCursor());
  QTextCursor::MoveMode mv_mode = QTextCursor::MoveAnchor;
  if(ext_select_on)
    mv_mode = QTextCursor::KeepAnchor;

  // no custom binding for these guys
  if (key_event->key() == Qt::Key_Return || key_event->key() == Qt::Key_Enter) {
    key_event->accept();
    if (waiting_for_key) {
      key_response = key_event->key();
      waiting_for_key = false;
    }
    else {
      if(promptDisp) {
        QString command = getCurrentCommand();
        if(isCommandComplete(command))
          execCommand(command, false);
      }
      else {
        displayPrompt(true);
      }
    }
    return;
  }

  switch(action) {
    case taiMisc::CONSOLE_UNDO:         // undo the current command
    case taiMisc::CONSOLE_UNDO_II:
      replaceCurrentCommand(QString());
      historyIndex = history.size();
      historyDraft.clear();
      ctrlCPressed();
      key_event->accept();
      displayPrompt();
      break;
    case taiMisc::CONSOLE_AUTO_COMPLETE:         // auto complete current command
    case taiMisc::CONSOLE_AUTO_COMPLETE_II:
    {
      key_event->accept();
      QString command = getCurrentCommand();
      QStringList sl = autocompleteCommand(command);
      QString intersect = findIntersection(sl);
      if(!intersect.isEmpty()) {
        command = intersect;
        replaceCurrentCommand(command);
      }
      if(sl.count() == 1) {
        replaceCurrentCommand(sl[0]);
      }
      else if(sl.count() > 1) {
        appendOutput(sl.join(" "), completionColor);
        replaceCurrentCommand(command);
      }
      break;
    }
    case taiMisc::CONSOLE_BACKSPACE:
    case taiMisc::CONSOLE_BACKSPACE_II:
      prepareCommandEdit();
      if(cursorInCurrentCommand()) {       // don't backup into prompt
        inherited::keyPressEvent(key_event);
      }
      else {
        key_event->accept();  // we are at the prompt - swallow
      }
      break;
    case taiMisc::CONSOLE_CLEAR:
    case taiMisc::CONSOLE_CLEAR_II:
      key_event->accept();
      clear();
      break;
    case taiMisc::CONSOLE_HISTORY_BACKWARD:
    case taiMisc::CONSOLE_HISTORY_BACKWARD_II:
      key_event->accept();
      if(history.size() > 0) {
        if(historyIndex == history.size())
          historyDraft = getCurrentCommand();
        historyIndex--; if(historyIndex < 0) historyIndex = 0;
        QString cmd = history[historyIndex];
        if(!cmd.isEmpty())
          replaceCurrentCommand(cmd);
      }
      break;
    case taiMisc::CONSOLE_HISTORY_FORWARD:
    case taiMisc::CONSOLE_HISTORY_FORWARD_II:
      key_event->accept();
      if(history.size() > 0) {
        historyIndex++; if(historyIndex > history.size()) historyIndex = history.size();
        replaceCurrentCommand(historyIndex == history.size() ? historyDraft : history[historyIndex]);
      }
      break;
      // these deselects don't work - rohrlich 11/20/14
    case taiMisc::CONSOLE_DESELECT:
    case taiMisc::CONSOLE_DESELECT_II:
      key_event->accept();
      cursor.clearSelection();
      setTextCursor(cursor);
      ext_select_on = true;
      break;
    case taiMisc::CONSOLE_CLEAR_SELECTION:
    case taiMisc::CONSOLE_CLEAR_SELECTION_II:
      key_event->accept();
      cursor.clearSelection();
      setTextCursor(cursor);
      ext_select_on = false;
      break;
    case taiMisc::CONSOLE_HOME:
    case taiMisc::CONSOLE_HOME_II:
      key_event->accept();
      gotoPrompt(cursor, ext_select_on);
      setTextCursor(cursor);
      break;
    case taiMisc::CONSOLE_END:
    case taiMisc::CONSOLE_END_II:
      key_event->accept();
      gotoEnd(cursor, ext_select_on);
      setTextCursor(cursor);
      break;
    case taiMisc::CONSOLE_CURSOR_FORWARD:
    case taiMisc::CONSOLE_CURSOR_FORWARD_II:
      key_event->accept();
      cursor.movePosition(QTextCursor::NextCharacter, mv_mode);
      setTextCursor(cursor);
      break;
    case taiMisc::CONSOLE_CURSOR_BACKWARD:
    case taiMisc::CONSOLE_CURSOR_BACKWARD_II:
      key_event->accept();
      cursor.movePosition(QTextCursor::PreviousCharacter, mv_mode);
      setTextCursor(cursor);
      break;
    case taiMisc::CONSOLE_DELETE:
    case taiMisc::CONSOLE_DELETE_II:
      key_event->accept();
      prepareCommandEdit();
      cursor = textCursor();
      cursor.deleteChar();
      setTextCursor(cursor);
      break;
    case taiMisc::CONSOLE_KILL:
    case taiMisc::CONSOLE_KILL_II:
    {
      key_event->accept();
      prepareCommandEdit();
      cursor = textCursor();
      cursor.movePosition(QTextCursor::EndOfLine, QTextCursor::KeepAnchor);
      QTextDocumentFragment frag = cursor.selection();
      MyQTextEditMimeData* md = new MyQTextEditMimeData(frag);
      QApplication::clipboard()->setMimeData(md);
      cursor.removeSelectedText();
      ext_select_on = false;
      break;
    }
    case taiMisc::CONSOLE_PASTE:
    case taiMisc::CONSOLE_PASTE_II:
      key_event->accept();
      paste();
      ext_select_on = false;
      break;
    case taiMisc::CONSOLE_CUT:
    case taiMisc::CONSOLE_CUT_II:
      key_event->accept();
      cut();
      ext_select_on = false;
      break;
    default:
      if(waiting_for_key) {
        key_response = key_event->key();
        waiting_for_key = false;
        key_event->accept();
      }
      else if(key_event->matches(QKeySequence::Cut)) {
        cut();
      }
      else if(key_event->matches(QKeySequence::Paste)) {
        paste();
      }
      else {
        if(!key_event->text().isEmpty() || key_event->key() == Qt::Key_Delete ||
           key_event->key() == Qt::Key_Backspace) {
          prepareCommandEdit();
          if(key_event->key() == Qt::Key_Backspace && !cursorInCurrentCommand()) {
            key_event->accept();
            break;
          }
        }
        inherited::keyPressEvent(key_event);
      }
  }

  // make sure we never go past prompt..
  QTextCursor end_cursor(textCursor());
  if(end_cursor.position() < curPromptPos) {
    gotoPrompt(end_cursor);
    setTextCursor(end_cursor);
  }
}

void iConsole::mousePressEvent(QMouseEvent *e) {
  setReadOnly(true);            // this is key for allowing links to be clicked
  inherited::mousePressEvent(e);
}

void iConsole::mouseMoveEvent(QMouseEvent *e) {
  inherited::mouseMoveEvent(e);
}

void iConsole::mouseReleaseEvent(QMouseEvent *e) {
  inherited::mouseReleaseEvent(e);
  setReadOnly(false);           // undo the RO for link clicking
  if(e->button() == Qt::MiddleButton) {
    const QClipboard::Mode mode = QApplication::clipboard()->supportsSelection()
      ? QClipboard::Selection : QClipboard::Clipboard;
    insertFromMimeData(QApplication::clipboard()->mimeData(mode));
  }
  else if(e->button() == Qt::LeftButton) {
    copy();                     // always copy!
  }
  // this is actually confusing to people -- just let it be..
//   QTextCursor cursor(textCursor());
//   // displays the prompt
//   gotoEnd(cursor, false);
//   setTextCursor(cursor);
}

void iConsole::contextMenuEvent(QContextMenuEvent *event) {
  QMenu menu(this);
  const bool selection = textCursor().hasSelection();
  menu.addAction(tr("Cu&t"), this, &iConsole::cut)->setEnabled(selection);
  menu.addAction(tr("&Copy"), this, &iConsole::copy)->setEnabled(selection);
  menu.addAction(tr("&Paste"), this, &iConsole::paste)->setEnabled(canPaste());
  menu.addSeparator();
  menu.addAction(tr("Select &All"), this, &iConsole::selectAll);
  menu.addAction(tr("&Clear All"), this, &iConsole::clear);
  taMisc::in_eventproc++;
  menu.exec(event->globalPos());
  taMisc::in_eventproc--;
}

//Get the current command
QString iConsole::getCurrentCommand() {
  QTextCursor cursor = textCursor();
  gotoPrompt(cursor);
  gotoEnd(cursor, true);
  QString command = cursor.selectedText();
  command.replace(QChar::ParagraphSeparator, QLatin1Char('\n'));
  cursor.clearSelection();
  return command;
}

//Replace current command with a new one
void iConsole::replaceCurrentCommand(QString newCommand) {
  QTextCursor cursor = textCursor();
  gotoPrompt(cursor);
  gotoEnd(cursor, true); // select
  cursor.insertText(newCommand);                                   // replaces
  cursor.clearSelection();
  setTextCursor(cursor);
  ensureCursorVisible();
}

bool iConsole::cursorInCurrentCommand() {
  QTextCursor cursor = textCursor();
  return cursor.hasSelection() ? cursor.selectionStart() >= curPromptPos
                               : cursor.position() > curPromptPos;
}

//execCommand(QString) executes the command and displays back its result
void iConsole::execCommand(QString command, bool writeCommand, bool showPrompt) {
  if(writeCommand) {
    displayPrompt();
    replaceCurrentCommand(command);
  }
  gotoEnd();
  promptDisp = false;
  executingCommand = true;
  int res = 0;
  QString strRes = interpretCommand(command, &res);
  if(!strRes.isEmpty())
    appendOutput(strRes, res == 0 ? outColor : errColor);
  flushOutput();
  executingCommand = false;
  if(showPrompt)
    displayPrompt();
}

int iConsole::saveContents(QString fileName) {
  quitPager = true;
  flushOutput();                // get anything pending
  QCoreApplication::processEvents();
  quitPager = false;
  QFile f(fileName);
  if (!f.open(QIODevice::WriteOnly))
    return -1;
  QTextStream ts(&f);
  ts << document()->toPlainText();
  f.close();
  return 0;
}

//saves a file script
int iConsole::saveScript(QString fileName) {
  QFile f(fileName);
  if (!f.open(QIODevice::WriteOnly))
    return -1;
  QTextStream ts(&f);
  for ( QStringList::Iterator it = recordedScript.begin(); it != recordedScript.end(); ++it)
    ts << *it << "\n";

  f.close();
  return 0;
}

//loads a file script
int iConsole::loadScript(QString fileName) {
  QFile f(fileName);
  if (!f.open(QIODevice::ReadOnly))
    return -1;
  QTextStream ts(&f);
  QString command;
  while(true) {
    command=ts.readLine();
    if (command.isNull())
      break; //done
    execCommand(command, true, false);
  }
  displayPrompt();
  f.close();
  return 0;
}

int iConsole::setStdLogfile(QString fileName) {
  if(logfile.isOpen()) {
    if(fileName.isNull())
      logfile.close();
    return 1;
  }
  logfile.setFileName(fileName);
  if (!logfile.open(QIODevice::WriteOnly))
    return -1;
  return 0;
}

// Only the text after the current prompt is editable. Mouse selections in
// previous output remain useful for copying, but cannot destroy the transcript.
void iConsole::prepareCommandEdit() {
  if(!promptDisp)
    displayPrompt();
  QTextCursor cursor = textCursor();
  if(cursor.hasSelection() && cursor.selectionEnd() > curPromptPos) {
    const int start = qMax(cursor.selectionStart(), curPromptPos);
    const int end = cursor.selectionEnd();
    cursor.setPosition(start);
    cursor.setPosition(end, QTextCursor::KeepAnchor);
  }
  else if(cursor.selectionStart() < curPromptPos) {
    cursor.movePosition(QTextCursor::End);
  }
  setTextCursor(cursor);
}

void iConsole::cut() {
  if(executingCommand || waiting_for_key) {
    copy();
    return;
  }
  if(textCursor().selectionEnd() <= curPromptPos) {
    copy();
    return;
  }
  prepareCommandEdit();
  inherited::cut();
}

void iConsole::paste() {
  insertFromMimeData(QApplication::clipboard()->mimeData());
}

void iConsole::insertFromMimeData(const QMimeData* source) {
  if(executingCommand || waiting_for_key || !source || !source->hasText())
    return;
  prepareCommandEdit();
  QTextCursor cursor = textCursor();
  cursor.insertText(source->text());
  setTextCursor(cursor);
  ensureCursorVisible();
}

void iConsole::inputMethodEvent(QInputMethodEvent* event) {
  if(executingCommand || waiting_for_key) {
    event->accept();
    return;
  }
  prepareCommandEdit();
  const int start = textCursor().position() + event->replacementStart();
  if(start < curPromptPos) {
    const int removedPrefix = curPromptPos - start;
    event->setCommitString(event->commitString(),
                          curPromptPos - textCursor().position(),
                          qMax(0, event->replacementLength() - removedPrefix));
  }
  inherited::inputMethodEvent(event);
}

void iConsole::dropEvent(QDropEvent* event) {
  if(executingCommand || waiting_for_key) {
    event->ignore();
    return;
  }
  if(event->mimeData()->hasText()) {
    insertFromMimeData(event->mimeData());
    event->setDropAction(Qt::CopyAction);
    event->accept();
  }
  else {
    event->ignore();
  }
}

///////////////////////////////////////////////////////
//  these need to be overridden by implementations,

//Basically, puts the command into the history list
//And emits a signal (should be called by reimplementations)
QString iConsole::interpretCommand(QString command, int *res) {
  //Add the command to the recordedScript list
  if(command.isEmpty() || (command == "\n")) return "";
  if (*res == 0)
    recordedScript.append(command);
  //update the history and its index
  history.append(command);
  historyIndex = history.size();
  historyDraft.clear();
  
  // write history to file for reloading
  // it is a bit excessive to save this every single command, OTOH there aren't many
  // typically and time take is minimal and it can be useful to make sure they are all in
  String filename = taMisc::prefs_dir + PATH_SEP + "console_history";
  QFile history_file(filename);
  if (history_file.open(QIODevice::Append)) {
    QTextStream out(&history_file);
    out << command << Qt::endl;
    history_file.close();
  }
  //emit the commandExecuted signal
  emit commandExecuted(command);
  return "";
}

// give suggestions to autocomplete a command (should be reimplemented)
// the return value of the function is the string list of all suggestions
QStringList iConsole::autocompleteCommand(QString) {
  return QStringList();
}

// note: implementations need to explicitly call this
QStringList iConsole::autocompleteFilename(QString cmd, QString pre_fnm) {
  QString path;
  QString fnm = cmd;
  if(cmd.contains('/')) {
    int pos = cmd.lastIndexOf('/');
    path = cmd.left(pos+1);
    fnm = cmd.right(cmd.size()-1 - pos);
  }
  else if(cmd.contains('\\')) {
    int pos = cmd.lastIndexOf('\\');
    path = cmd.left(pos+1);
    fnm = cmd.right(cmd.size()-1 - pos);
  }
  int fnmlen = fnm.length();
  QStringList lst;
  QDir dir(path);
  QStringList files = dir.entryList();
  for(int i=0;i<files.size();i++) {
    QString fl = files[i];
    if(fl.left(fnmlen) == fnm)
      lst.append(pre_fnm + path + fl);
  }
  return lst;
}

static QString StringIntersect(QString str1, QString str2) {
  int mxlen = qMin(str1.length(), str2.length());
  int i;
  for(i=0;i<mxlen;i++) {
    if(str1[i] != str2[i]) break;
  }
  if(i > 0)
    return str1.left(i);
  return "";
}

QString iConsole::findIntersection(const QStringList& lst) {
  if(lst.size() == 0) return "";
  if(lst.size() == 1) return lst[0];
  QString isect = lst[0];
  for(int i=1;i<lst.size();i++) {
    isect = StringIntersect(isect, lst[i]);
  }
  return isect;
}

void iConsole::linkClicked(const QUrl & link) {
  // QString path = link.path(); // will only be part before #, if any
  // outputLine(path, true);
  QDesktopServices::openUrl(link);
}

//default implementation: command always complete
bool iConsole::isCommandComplete(QString cmd) { (void)cmd;
//   if(cmd.isEmpty()) return false;
  return true;
}

// implementation should do something here..
void iConsole::ctrlCPressed() {
}
