// event_bus/event_publisher.h — Thread-safe event publisher
#pragma once

#include "brain_core/event_bus/domain_event.h"
#include <queue>
#include <mutex>
#include <functional>
#include <vector>

namespace brain_core {

/// EventBus publisher: dispatches domain events to registered handlers.
/// Thread-safe for concurrent publish/subscribe.
class EventPublisher {
public:
    using EventHandler = std::function<void(const TypedDomainEvent&)>;

    EventPublisher();

    /// Publish an event (thread-safe).
    void publish(const TypedDomainEvent& event);

    /// Publish with priority (higher priority events skip queue).
    void publishPriority(const TypedDomainEvent& event, EventPriority prio);

    /// Register a global event handler.
    void subscribe(EventHandler handler);

    /// Subscribe to a specific event type.
    void subscribe(EventType type, EventHandler handler);

    /// Get the number of queued events.
    size_t pendingCount() const;

    /// Drain all queued events (call in main loop).
    void drain();

    /// Clear all handlers.
    void clearHandlers();

private:
    struct QueuedEvent {
        TypedDomainEvent event;
        EventPriority priority{EventPriority::NORMAL};
    };

    std::queue<QueuedEvent> _queue;
    std::vector<EventHandler> _handlers;
    std::unordered_map<EventType, std::vector<EventHandler>> _typed_handlers;
    mutable std::mutex _mutex;
};

} // namespace brain_core
