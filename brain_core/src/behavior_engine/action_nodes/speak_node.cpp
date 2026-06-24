// action_nodes/speak_node.cpp
#include "brain_core/behavior_engine/action_nodes/speak_node.h"
#include <iostream>

namespace brain_core {

SpeakNode::SpeakNode()
{
    std::cout << "[SpeakNode] Initialized." << std::endl;
}

void SpeakNode::setMessage(const std::string& text)
{
    std::lock_guard<std::mutex> lock(_mutex);
    _message = text;
    std::cout << "[SpeakNode] Message: \"" << text << "\"" << std::endl;
}

void SpeakNode::enqueueMessage(const std::string& text)
{
    std::lock_guard<std::mutex> lock(_mutex);
    _queue.push(text);
}

BTNodeStatus SpeakNode::execute()
{
    std::lock_guard<std::mutex> lock(_mutex);

    if (!_active) {
        _active = true;
        // Pick next message: explicit set > queue > empty
        if (!_message.empty()) {
            std::cout << "[SpeakNode] Speaking: \"" << _message << "\"" << std::endl;
            _speaking = true;
            return BTNodeStatus::RUNNING;
        } else if (!_queue.empty()) {
            _message = _queue.front();
            _queue.pop();
            std::cout << "[SpeakNode] Speaking (queued): \"" << _message << "\"" << std::endl;
            _speaking = true;
            return BTNodeStatus::RUNNING;
        }
        return BTNodeStatus::SUCCESS;  // nothing to say
    }

    // Simulate TTS completion after one tick
    _speaking = false;
    _message.clear();
    _active   = false;
    return BTNodeStatus::SUCCESS;
}

void SpeakNode::cancel()
{
    std::lock_guard<std::mutex> lock(_mutex);
    _active   = false;
    _speaking = false;
}

void SpeakNode::clearQueue()
{
    std::lock_guard<std::mutex> lock(_mutex);
    while (!_queue.empty()) _queue.pop();
}

} // namespace brain_core
