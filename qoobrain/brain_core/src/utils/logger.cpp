// utils/logger.cpp — Structured logging
#include "brain_core/utils/logger.h"
#include <iostream>
#include <iomanip>

namespace brain_core {

Logger::Logger()
{
    std::cout << "[Logger] Initialized." << std::endl;
}

void Logger::init(const std::string& log_file)
{
    std::lock_guard<std::mutex> lock(_mutex);
    if (!log_file.empty()) {
        _file.open(log_file, std::ios::app);
        _use_file = _file.is_open();
    }
}

void Logger::setLevel(LogLevel level)
{
    _min_level = level;
}

void Logger::log(LogLevel level, const std::string& module,
                  const std::string& message)
{
    if (static_cast<int>(level) < static_cast<int>(_min_level)) return;

    std::lock_guard<std::mutex> lock(_mutex);

    std::stringstream ss;
    ss << "[" << _timestamp() << "]"
       << " [" << _levelToString(level) << "]"
       << " [" << module << "] "
       << message;

    auto& out = (level >= LogLevel::ERROR) ? std::cerr : std::cout;
    out << ss.str() << std::endl;

    if (_use_file && _file.is_open()) {
        _file << ss.str() << std::endl;
    }
}

void Logger::debug(const std::string& module, const std::string& msg)
    { log(LogLevel::DEBUG, module, msg); }

void Logger::info(const std::string& module, const std::string& msg)
    { log(LogLevel::INFO, module, msg); }

void Logger::warning(const std::string& module, const std::string& msg)
    { log(LogLevel::WARNING, module, msg); }

void Logger::error(const std::string& module, const std::string& msg)
    { log(LogLevel::ERROR, module, msg); }

void Logger::critical(const std::string& module, const std::string& msg)
    { log(LogLevel::CRITICAL, module, msg); }

Logger& Logger::instance()
{
    static Logger logger;
    return logger;
}

std::string Logger::_levelToString(LogLevel level)
{
    switch (level) {
        case LogLevel::DEBUG:    return "DEBUG";
        case LogLevel::INFO:     return "INFO";
        case LogLevel::WARNING:  return "WARN";
        case LogLevel::ERROR:    return "ERROR";
        case LogLevel::CRITICAL: return "CRIT";
    }
    return "UNKN";
}

std::string Logger::_timestamp() const
{
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()) % 1000;

    std::stringstream ss;
    ss << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S");
    ss << "." << std::setw(3) << std::setfill('0') << ms.count();
    return ss.str();
}

} // namespace brain_core
