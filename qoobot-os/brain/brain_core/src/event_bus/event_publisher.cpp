// event_publisher.cpp — Thread-safe event publisher
#include "brain_core/event_bus/event_publisher.h"
#include <iostream>
#include <algorithm>

namespace brain_core {

EventPublisher::EventPublisher()
{
    std::cout << "[EventPublisher] Initialized." << std::endl;
}

void EventPublisher::publish(const TypedDomainEvent& event)
{
    std::lock_guard<std::mutex> lock(_mutex);

    // Notify typed handlers immediately
    auto it = _typed_handlers.find(event.type);
    if (it != _typed_handlers.end()) {
        for (auto& h : it->second) {
            h(event);
        }
    }

    // Queue for global handlers
    _queue.push({event, EventPriority::NORMAL});
}

void EventPublisher::publishPriority(const TypedDomainEvent& event,
                                      EventPriority prio)
{
    std::lock_guard<std::mutex> lock(_mutex);

    // Critical events are dispatched immediately
    if (prio == EventPriority::CRITICAL) {
        for (auto& h : _handlers) {
            h(event);
        }
        auto it = _typed_handlers.find(event.type);
        if (it != _typed_handlers.end()) {
            for (auto& h : it->second) {
                h(event);
            }
        }
        return;
    }

    _queue.push({event, prio});
}

void EventPublisher::subscribe(EventHandler handler)
{
    std::lock_guard<std::mutex> lock(_mutex);
    _handlers.push_back(std::move(handler));
}

void EventPublisher::subscribe(EventType type, EventHandler handler)
{
    std::lock_guard<std::mutex> lock(_mutex);
    _typed_handlers[type].push_back(std::move(handler));
}

size_t EventPublisher::pendingCount() const
{
    std::lock_guard<std::mutex> lock(_mutex);
    return _queue.size();
}

void EventPublisher::drain()
{
    std::lock_guard<std::mutex> lock(_mutex);

    while (!_queue.empty()) {
        auto qe = _queue.front();
        _queue.pop();

        for (auto& h : _handlers) {
            h(qe.event);
        }
    }
}

void EventPublisher::clearHandlers()
{
    std::lock_guard<std::mutex> lock(_mutex);
    _handlers.clear();
    _typed_handlers.clear();
}

} // namespace brain_core
