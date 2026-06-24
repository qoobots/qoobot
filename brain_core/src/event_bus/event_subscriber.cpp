// event_subscriber.cpp — Event subscription & filtering
#include "brain_core/event_bus/event_subscriber.h"
#include <iostream>
#include <algorithm>

namespace brain_core {

EventSubscriber::EventSubscriber()
{
    std::cout << "[EventSubscriber] Initialized." << std::endl;
}

void EventSubscriber::subscribe(EventCallback cb, EventFilter filter)
{
    std::lock_guard<std::mutex> lock(_mutex);
    _subscriptions.push_back({std::move(cb), std::move(filter), {}});
}

void EventSubscriber::subscribeTo(std::vector<EventType> types, EventCallback cb)
{
    std::lock_guard<std::mutex> lock(_mutex);
    _subscriptions.push_back({std::move(cb), nullptr, std::move(types)});
}

void EventSubscriber::receive(const TypedDomainEvent& event)
{
    std::lock_guard<std::mutex> lock(_mutex);

    bool dispatched = false;
    for (auto& sub : _subscriptions) {
        // Type filter
        if (!sub.types.empty()) {
            if (std::find(sub.types.begin(), sub.types.end(), event.type) == sub.types.end()) {
                continue;
            }
        }

        // Custom filter
        if (sub.filter && !sub.filter(event)) {
            continue;
        }

        sub.callback(event);
        dispatched = true;
    }

    if (!dispatched) {
        // Buffer unmatched events
        _buffer.push_back(event);
    }
}

size_t EventSubscriber::bufferSize() const
{
    std::lock_guard<std::mutex> lock(_mutex);
    return _buffer.size();
}

std::vector<TypedDomainEvent> EventSubscriber::drain()
{
    std::lock_guard<std::mutex> lock(_mutex);
    std::vector<TypedDomainEvent> drained;
    drained.swap(_buffer);
    return drained;
}

void EventSubscriber::clear()
{
    std::lock_guard<std::mutex> lock(_mutex);
    _subscriptions.clear();
    _buffer.clear();
}

} // namespace brain_core
