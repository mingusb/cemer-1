// Copyright 2016-2018, Regents of the University of Colorado,
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

#include "taSound_QObj.h"

#if (QT_VERSION >= 0x050000)

#include <taSound>
#include <QAudioDecoder>
#include <QAudioFormat>
#include <QAudioSink>
#include <QAudioDevice>
#include <QMediaDevices>
#include <QUrl>
#include <QBuffer>
#include <QByteArray>

#include <taMisc>

taSound_QObj::taSound_QObj(taSound* snd) {
  sound = snd;
  decoder = NULL;
  output = NULL;
  out_buff = NULL;
  done_loading = false;
}

taSound_QObj::~taSound_QObj() {
  // these are parented to us so they die with us.
  // if(decoder) delete decoder;
  // if(output) delete output;
  sound = NULL;
  decoder = NULL;
  output = NULL;
}


bool taSound_QObj::LoadSound(const QString& fname) {
  if(decoder) {
    delete decoder;
  }
  decoder = new QAudioDecoder(this);
  sound->q_buf = QAudioBuffer();
  decoded_data.clear();
  decoded_format = QAudioFormat();
  decoder->setSource(QUrl::fromLocalFile(fname));
  connect(decoder, &QAudioDecoder::bufferReady, this, [this]() {
    const QAudioBuffer buffer = decoder->read();
    if(buffer.isValid()) {
      decoded_format = buffer.format();
      decoded_data.append(buffer.constData<char>(), buffer.byteCount());
    }
  });

  connect(decoder, &QAudioDecoder::finished, this, &taSound_QObj::LoadFinished);

  connect(decoder, qOverload<QAudioDecoder::Error>(&QAudioDecoder::error),
          this, &taSound_QObj::LoadError);

  done_loading = false;
  
  decoder->start();

  while(!done_loading) {
    taMisc::RunPending();
  }
  return sound->q_buf.isValid(); // todo: could have local err flag too
}

void taSound_QObj::LoadFinished() {
  if(decoded_data.isEmpty()) {
    LoadError();
    return;
  }
  sound->q_buf = QAudioBuffer(decoded_data, decoded_format);
  decoder->disconnect(this);
  decoder->deleteLater();
  decoder = NULL;
  done_loading = true;
}

void taSound_QObj::LoadError() {
  taMisc::Error("Sound file not loadable for sound:", sound->name,
                "file:", decoder->source().toLocalFile().toLatin1(), "err msg:",
                decoder->errorString().toLatin1());
  decoder->disconnect(this);
  decoder->deleteLater();
  decoder = NULL;
  done_loading = true;
}

bool taSound_QObj::PlaySound(const QString& device_name) {
  if(output) {
    taMisc::Error("PlaySound for sound:", sound->name, "sound is currently still being played");
    return false;
  }
  if(device_name.isEmpty()) {
    output = new QAudioSink(sound->q_buf.format(), this);
  }
  else {
    QList<QAudioDevice> devs = QMediaDevices::audioOutputs();
    QAudioDevice ad;
    for(int i=0; i<devs.count(); i++) {
      if(devs[i].description() == device_name) {
        ad = devs[i];
        break;
      }
    }
    if(ad.isNull()) {
      taMisc::Error("Audio output device not found:", device_name);
      return false;
    }
    output = new QAudioSink(ad, sound->q_buf.format(), this);
  }
  // Keep playback data alive even if the sound is replaced while the sink runs.
  out_bary = QByteArray(sound->q_buf.constData<char>(), sound->q_buf.byteCount());
  out_buff = new QBuffer(&out_bary, output);
  out_buff->open(QIODevice::ReadOnly);

  connect(output, &QAudioSink::stateChanged, this, &taSound_QObj::PlayStateChanged);
  output->start(out_buff);
  return true;
}

void taSound_QObj::PlayStateChanged(QAudio::State newState) {
  if(!output) return;
  if(newState != QAudio::IdleState && newState != QAudio::StoppedState)
    return;
  if(newState == QAudio::IdleState && !out_buff->atEnd())
    return;
  // Detach first: stop() can synchronously emit another stateChanged signal.
  QAudioSink* finishedOutput = output;
  QBuffer* finishedBuffer = out_buff;
  const QAudio::Error error = finishedOutput->error();
  output = NULL;
  out_buff = NULL;
  finishedOutput->disconnect(this);
  finishedOutput->stop();
  finishedBuffer->close();
  finishedOutput->deleteLater();
  if(error != QAudio::NoError)
    taMisc::Error("Error playing sound:", sound->name, "Code:", String(error));
}

#else  // (QT_VERSION >= 0x050000)

taSound_QObj::taSound_QObj(taSound* snd) {
}

#endif // (QT_VERSION >= 0x050000)
