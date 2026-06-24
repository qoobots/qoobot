// action_nodes/speak_node.h — Text-to-speech output for user feedback
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <queue>
#include <mutex>

namespace brain_core {

class SpeakNode {
public:
    SpeakNode();

    /// Set the message to speak.
    void setMessage(const std::string& text);

    /// Queue a message for later playback.
    void enqueueMessage(const std::string& text);

    /// Execute TTS playback. Returns RUNNING during speech,
    /// SUCCESS when done, FAILURE on TTS error.
    BTNodeStatus execute();

    /// Cancel current speech.
    void cancel();

    /// Check if currently speaking.
    bool isSpeaking() const { return _speaking; }

    /// Clear all queued messages.
    void clearQueue();

private:
    std::string _message;
    std::queue<std::string> _queue;
    std::mutex _mutex;
    bool _speaking{false};
    bool _active{false};
};

} // namespace brain_core
