#pragma once

#include "error_codes.h"
#include <optional>
#include <string>
#include <variant>

namespace qoosvc {

/**
 * Result<T> — Rust-like result type for error handling.
 * Either holds a value of type T or an error.
 */
template <typename T>
class Result {
public:
    // Success constructor
    static Result<T> ok(T value) {
        Result<T> r;
        r.data_ = std::move(value);
        return r;
    }

    // Error constructor
    static Result<T> err(ErrorCode code, std::string message = {}) {
        Result<T> r;
        r.error_code_ = code;
        r.error_message_ = message.empty() ? std::string(error_code_message(code)) : std::move(message);
        return r;
    }

    bool is_ok() const { return data_.has_value(); }
    bool is_err() const { return !is_ok(); }

    T& value() { return data_.value(); }
    const T& value() const { return data_.value(); }

    T& operator*() { return value(); }
    const T& operator*() const { return value(); }

    T* operator->() { return &value(); }
    const T* operator->() const { return &value(); }

    ErrorCode error_code() const { return error_code_; }
    const std::string& error_message() const { return error_message_; }

    /**
     * Unwrap or return default value on error.
     */
    T unwrap_or(T default_value) const {
        return is_ok() ? data_.value() : std::move(default_value);
    }

private:
    Result() = default;
    std::optional<T> data_;
    ErrorCode error_code_ = ErrorCode::OK;
    std::string error_message_;
};

/**
 * Specialization for void (no value on success).
 */
template <>
class Result<void> {
public:
    static Result<void> ok() {
        Result<void> r;
        r.success_ = true;
        return r;
    }

    static Result<void> err(ErrorCode code, std::string message = {}) {
        Result<void> r;
        r.success_ = false;
        r.error_code_ = code;
        r.error_message_ = message.empty() ? std::string(error_code_message(code)) : std::move(message);
        return r;
    }

    bool is_ok() const { return success_; }
    bool is_err() const { return !success_; }

    ErrorCode error_code() const { return error_code_; }
    const std::string& error_message() const { return error_message_; }

private:
    Result() = default;
    bool success_ = false;
    ErrorCode error_code_ = ErrorCode::OK;
    std::string error_message_;
};

} // namespace qoosvc
