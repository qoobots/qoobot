// event_bus/event_subscriber.h — Event subscription & filtering
#pragma once

#include "brain_core/event_bus/domain_event.h"
#include <functional>
#include <vector>
#include <mutex>

namespace brain_core {

/// Standalone subscriber that can filter and buffer events.
class EventSubscriber {
public:
    using EventCallback = std::function<void(const TypedDomainEvent&)>;
    using EventFilter   = std::function<bool(const TypedDomainEvent&)>;

    EventSubscriber();

    /// Subscribe to all events with an optional filter.
    void subscribe(EventCallback cb, EventFilter filter = nullptr);

    /// Subscribe to specific event types.
    void subscribeTo(std::vector<EventType> types, EventCallback cb);

    /// Receive and dispatch an event.
    void receive(const TypedDomainEvent& event);

    /// Get buffered event count.
    size_t bufferSize() const;

    /// Drain all buffered events.
    std::vector<TypedDomainEvent> drain();

    /// Clear all subscriptions.
    void clear();

private:
    struct Subscription {
        EventCallback callback;
        EventFilter   filter;
        std::vector<EventType> types;  // empty = all types
    };

    std::vector<Subscription> _subscriptions;
    std::vector<TypedDomainEvent> _buffer;
    mutable std::mutex _mutex;
};

} // namespace brain_core
