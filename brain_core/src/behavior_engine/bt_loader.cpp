// behavior_engine/bt_loader.cpp — BT XML loading, validation & preprocessing
#include "brain_core/behavior_engine/bt_loader.h"
#include <fstream>
#include <sstream>
#include <iostream>
#include <regex>
#include <set>

namespace brain_core {

std::optional<std::string> BTLoader::loadXML(const std::string& path)
{
    std::ifstream file(path);
    if (!file.is_open()) {
        _last_error = "Cannot open file: " + path;
        std::cerr << "[BTLoader] " << _last_error << std::endl;
        return std::nullopt;
    }
    std::stringstream buffer;
    buffer << file.rdbuf();
    std::string raw = buffer.str();
    std::cout << "[BTLoader] Loaded " << raw.size() << " bytes from " << path << std::endl;
    return preprocess(raw);
}

std::string BTLoader::loadFromString(const std::string& xml)
{
    std::cout << "[BTLoader] Loading from string (" << xml.size() << " bytes)" << std::endl;
    return preprocess(xml);
}

std::string BTLoader::preprocess(const std::string& raw_xml)
{
    std::string result = raw_xml;

    // Strip markdown code fences (```xml ... ```)
    std::regex fence_re(R"(```(?:xml)?\s*\n(.*?)\n\s*```)", std::regex::icase);
    std::smatch match;
    if (std::regex_search(result, match, fence_re)) {
        result = match[1].str();
    }

    // Strip leading/trailing whitespace but preserve internal structure
    auto start = result.find_first_not_of(" \t\n\r");
    auto end   = result.find_last_not_of(" \t\n\r");
    if (start != std::string::npos && end != std::string::npos) {
        result = result.substr(start, end - start + 1);
    }

    return result;
}

bool BTLoader::validateXML(const std::string& xml)
{
    _last_error.clear();

    if (xml.empty()) {
        _last_error = "Empty XML content";
        return false;
    }

    if (!_validate_tags(xml)) return false;
    if (!_validate_structure(xml)) return false;

    std::cout << "[BTLoader] XML validation passed." << std::endl;
    return true;
}

bool BTLoader::_validate_tags(const std::string& xml)
{
    // Check for root <root> element (BehaviorTree.CPP convention)
    bool has_root_open  = xml.find("<root")  != std::string::npos;
    bool has_root_close = xml.find("</root>") != std::string::npos;
    if (!has_root_open || !has_root_close) {
        _last_error = "Missing <root>...</root> wrapper";
        return false;
    }

    // Check for <BehaviorTree> element
    bool has_bt = xml.find("<BehaviorTree") != std::string::npos;
    if (!has_bt) {
        _last_error = "Missing <BehaviorTree> element";
        return false;
    }

    return true;
}

bool BTLoader::_validate_structure(const std::string& xml)
{
    // Check for unmatched tags
    size_t open_count  = 0;
    size_t close_count = 0;
    std::regex tag_re(R"(</?[A-Za-z_][A-Za-z0-9_]*)");
    auto it = std::sregex_iterator(xml.begin(), xml.end(), tag_re);
    auto end = std::sregex_iterator();
    for (; it != end; ++it) {
        std::string tag = it->str();
        if (tag[1] == '/') close_count++;
        else open_count++;
    }
    // This is a rough check; full XML parsing would be heavier
    if (open_count != close_count) {
        _last_error = "Unmatched XML tags (open=" + std::to_string(open_count)
                    + ", close=" + std::to_string(close_count) + ")";
        std::cerr << "[BTLoader] Warning: " << _last_error << std::endl;
        // Don't hard-fail on this — LLM-generated XML may have quirks
    }

    return true;
}

} // namespace brain_core
