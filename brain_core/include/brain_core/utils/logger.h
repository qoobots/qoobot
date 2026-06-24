// utils/logger.h — Structured logging utility
#pragma once

#include <string>
#include <chrono>
#include <fstream>
#include <mutex>
#include <sstream>

namespace brain_core {

/// Log severity levels.
enum class LogLevel {
    DEBUG,
    INFO,
    WARNING,
    ERROR,
    CRITICAL,
};

class Logger {
public:
    Logger();

    /// Initialize logger with output file (optional).
    void init(const std::string& log_file = "");

    /// Set minimum log level (default: INFO).
    void setLevel(LogLevel level);

    /// Log a message with level and source module.
    void log(LogLevel level, const std::string& module,
             const std::string& message);

    /// Convenience methods.
    void debug(const std::string& module, const std::string& msg);
    void info(const std::string& module, const std::string& msg);
    void warning(const std::string& module, const std::string& msg);
    void error(const std::string& module, const std::string& msg);
    void critical(const std::string& module, const std::string& msg);

    /// Get the singleton instance.
    static Logger& instance();

private:
    static std::string _levelToString(LogLevel level);
    std::string _timestamp() const;

    LogLevel _min_level{LogLevel::INFO};
    std::ofstream _file;
    std::mutex _mutex;
    bool _use_file{false};
};

} // namespace brain_core
