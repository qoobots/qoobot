// event_bus/domain_event.h — Domain event type definitions
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <any>
#include <optional>

namespace brain_core {

/// Extended domain event with typed payload support.
struct TypedDomainEvent {
    EventType   type;
    std::string source_node;
    std::string payload_json;      // JSON serialized payload
    std::any    typed_payload;     // C++ typed payload (optional)
    std::chrono::system_clock::time_point timestamp;
};

/// Event priority for ordering.
enum class EventPriority {
    LOW      = 0,
    NORMAL   = 1,
    HIGH     = 2,
    CRITICAL = 3,   // e.g., emergency stop
};

} // namespace brain_core
