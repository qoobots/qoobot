// behavior_engine/bt_loader.h — BehaviorTree XML loader & validator
#pragma once

#include <string>
#include <optional>

namespace brain_core {

/// Loads, validates, and preprocesses BehaviorTree.CPP XML files.
/// Supports LLM-generated XML with optional schema validation.
class BTLoader {
public:
    BTLoader() = default;

    /// Load XML from file path; returns content on success.
    std::optional<std::string> loadXML(const std::string& path);

    /// Load XML from raw string (e.g., gRPC payload).
    std::string loadFromString(const std::string& xml);

    /// Validate XML against BehaviorTree.CPP schema.
    /// Checks: root <BehaviorTree> tag, valid control/action nodes,
    /// no circular references, all referenced nodes exist.
    bool validateXML(const std::string& xml);

    /// Preprocess LLM-generated XML: strip markdown fences,
    /// normalize whitespace, expand shorthand node names.
    std::string preprocess(const std::string& raw_xml);

    /// Get last validation error message.
    const std::string& lastError() const { return _last_error; }

private:
    bool _validate_tags(const std::string& xml);
    bool _validate_structure(const std::string& xml);

    std::string _last_error;
};

} // namespace brain_core
