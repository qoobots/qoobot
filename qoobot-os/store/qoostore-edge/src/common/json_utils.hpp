/**
 * json_utils.hpp — 轻量级 JSON 读写工具
 *
 * 无外部依赖，纯 C++17 实现。用于 qoostore-edge 中技能注册表、
 * 权限存储、manifest 解析等场景的 JSON 序列化/反序列化。
 *
 * 支持：
 *   - 对象/数组/字符串/数字/布尔/null 的读写
 *   - 嵌套结构递归解析
 *   - 流式写入（内存友好）
 *   - 错误位置报告
 *
 * 对标：nlohmann/json 的核心功能子集，但为嵌入式环境优化。
 */

#pragma once

#include <string>
#include <string_view>
#include <vector>
#include <map>
#include <variant>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <cstdint>
#include <cmath>
#include <cctype>
#include <iomanip>

namespace qoostore::edge::json {

// ============================================================================
// 类型定义
// ============================================================================

class Value;

using Null = std::nullptr_t;
using Object = std::map<std::string, Value>;
using Array = std::vector<Value>;
using String = std::string;
using Number = double;
using Boolean = bool;

/**
 * JSON 值类型
 */
enum class Type {
    Null,
    Object,
    Array,
    String,
    Number,
    Boolean
};

/**
 * JSON 解析异常
 */
class ParseError : public std::runtime_error {
public:
    ParseError(const std::string& msg, size_t pos = 0)
        : std::runtime_error(msg + " at position " + std::to_string(pos)), pos_(pos) {}
    size_t position() const { return pos_; }
private:
    size_t pos_;
};

// ============================================================================
// Value — 统一 JSON 值类型
// ============================================================================

class Value {
public:
    using variant_t = std::variant<Null, Object, Array, String, Number, Boolean>;

    Value() : data_(nullptr) {}
    Value(Null) : data_(nullptr) {}
    Value(Object v) : data_(std::move(v)) {}
    Value(Array v) : data_(std::move(v)) {}
    Value(String v) : data_(std::move(v)) {}
    Value(const char* v) : data_(String(v)) {}
    Value(Number v) : data_(v) {}
    Value(int v) : data_(static_cast<Number>(v)) {}
    Value(int64_t v) : data_(static_cast<Number>(v)) {}
    Value(uint64_t v) : data_(static_cast<Number>(v)) {}
    Value(Boolean v) : data_(v) {}

    Type type() const {
        return std::visit([](const auto& v) -> Type {
            using T = std::decay_t<decltype(v)>;
            if constexpr (std::is_same_v<T, Null>) return Type::Null;
            else if constexpr (std::is_same_v<T, Object>) return Type::Object;
            else if constexpr (std::is_same_v<T, Array>) return Type::Array;
            else if constexpr (std::is_same_v<T, String>) return Type::String;
            else if constexpr (std::is_same_v<T, Number>) return Type::Number;
            else if constexpr (std::is_same_v<T, Boolean>) return Type::Boolean;
        }, data_);
    }

    bool is_null() const { return type() == Type::Null; }
    bool is_object() const { return type() == Type::Object; }
    bool is_array() const { return type() == Type::Array; }
    bool is_string() const { return type() == Type::String; }
    bool is_number() const { return type() == Type::Number; }
    bool is_bool() const { return type() == Type::Boolean; }

    // 类型安全访问
    Object& as_object() { return std::get<Object>(data_); }
    const Object& as_object() const { return std::get<Object>(data_); }
    Array& as_array() { return std::get<Array>(data_); }
    const Array& as_array() const { return std::get<Array>(data_); }
    String& as_string() { return std::get<String>(data_); }
    const String& as_string() const { return std::get<String>(data_); }
    Number as_number() const { return std::get<Number>(data_); }
    Boolean as_bool() const { return std::get<Boolean>(data_); }
    int64_t as_int() const { return static_cast<int64_t>(as_number()); }
    uint64_t as_uint() const { return static_cast<uint64_t>(as_number()); }

    // 便捷访问 operator[]
    Value& operator[](const std::string& key) {
        if (!is_object()) data_ = Object{};
        return as_object()[key];
    }
    const Value& operator[](const std::string& key) const {
        static Value null_val;
        if (!is_object()) return null_val;
        auto it = as_object().find(key);
        return it != as_object().end() ? it->second : null_val;
    }

    Value& operator[](size_t index) {
        if (!is_array()) data_ = Array{};
        auto& arr = as_array();
        if (index >= arr.size()) arr.resize(index + 1);
        return arr[index];
    }

    // 带默认值的类型获取
    String get_string(const std::string& key, const String& def = "") const {
        auto& v = (*this)[key];
        return v.is_string() ? v.as_string() : def;
    }
    int64_t get_int(const std::string& key, int64_t def = 0) const {
        auto& v = (*this)[key];
        return v.is_number() ? v.as_int() : def;
    }
    bool get_bool(const std::string& key, bool def = false) const {
        auto& v = (*this)[key];
        return v.is_bool() ? v.as_bool() : def;
    }
    bool has(const std::string& key) const {
        return is_object() && as_object().count(key) > 0;
    }

    size_t size() const {
        if (is_object()) return as_object().size();
        if (is_array()) return as_array().size();
        return 0;
    }

    // 序列化
    std::string dump(int indent = 0) const {
        std::ostringstream oss;
        dump_internal(oss, indent, 0);
        return oss.str();
    }

private:
    variant_t data_;

    void dump_internal(std::ostringstream& oss, int indent, int depth) const {
        std::visit([&](const auto& v) {
            using T = std::decay_t<decltype(v)>;
            if constexpr (std::is_same_v<T, Null>) {
                oss << "null";
            } else if constexpr (std::is_same_v<T, Object>) {
                dump_object(oss, v, indent, depth);
            } else if constexpr (std::is_same_v<T, Array>) {
                dump_array(oss, v, indent, depth);
            } else if constexpr (std::is_same_v<T, String>) {
                oss << '"' << escape_string(v) << '"';
            } else if constexpr (std::is_same_v<T, Number>) {
                if (std::isnan(v) || std::isinf(v)) oss << "null";
                else oss << v;
            } else if constexpr (std::is_same_v<T, Boolean>) {
                oss << (v ? "true" : "false");
            }
        }, data_);
    }

    static void dump_object(std::ostringstream& oss, const Object& obj, int indent, int depth) {
        if (obj.empty()) { oss << "{}"; return; }
        oss << "{";
        bool first = true;
        for (const auto& [k, v] : obj) {
            if (!first) oss << ",";
            first = false;
            if (indent > 0) {
                oss << "\n" << std::string((depth + 1) * indent, ' ');
            }
            oss << '"' << escape_string(k) << "\":";
            if (indent > 0) oss << " ";
            v.dump_internal(oss, indent, depth + 1);
        }
        if (indent > 0) oss << "\n" << std::string(depth * indent, ' ');
        oss << "}";
    }

    static void dump_array(std::ostringstream& oss, const Array& arr, int indent, int depth) {
        if (arr.empty()) { oss << "[]"; return; }
        oss << "[";
        bool first = true;
        for (const auto& v : arr) {
            if (!first) oss << ",";
            first = false;
            if (indent > 0) oss << "\n" << std::string((depth + 1) * indent, ' ');
            v.dump_internal(oss, indent, depth + 1);
        }
        if (indent > 0) oss << "\n" << std::string(depth * indent, ' ');
        oss << "]";
    }

    static std::string escape_string(const std::string& s) {
        std::string result;
        result.reserve(s.size());
        for (char c : s) {
            switch (c) {
                case '"': result += "\\\""; break;
                case '\\': result += "\\\\"; break;
                case '\b': result += "\\b"; break;
                case '\f': result += "\\f"; break;
                case '\n': result += "\\n"; break;
                case '\r': result += "\\r"; break;
                case '\t': result += "\\t"; break;
                default:
                    if (static_cast<unsigned char>(c) < 0x20)
                        result += "\\u00" + hex2(c >> 4) + hex2(c & 0xF);
                    else
                        result += c;
            }
        }
        return result;
    }

    static std::string hex2(int v) {
        std::ostringstream oss;
        oss << std::hex << std::uppercase << std::setw(2) << std::setfill('0') << (v & 0xFF);
        return oss.str();
    }
};

// ============================================================================
// Parser — JSON 解析器
// ============================================================================

class Parser {
public:
    static Value parse(const std::string& json) {
        Parser p(json);
        Value v = p.parse_value();
        p.skip_whitespace();
        if (p.pos_ < p.json_.size()) {
            throw ParseError("Unexpected trailing content", p.pos_);
        }
        return v;
    }

private:
    std::string_view json_;
    size_t pos_;

    Parser(std::string_view json) : json_(json), pos_(0) {}

    void skip_whitespace() {
        while (pos_ < json_.size() && std::isspace(json_[pos_])) {
            ++pos_;
        }
    }

    char peek() {
        skip_whitespace();
        return pos_ < json_.size() ? json_[pos_] : '\0';
    }

    char advance() {
        return pos_ < json_.size() ? json_[pos_++] : '\0';
    }

    void expect(char c) {
        skip_whitespace();
        if (pos_ >= json_.size() || json_[pos_] != c) {
            throw ParseError(std::string("Expected '") + c + "'", pos_);
        }
        ++pos_;
    }

    Value parse_value() {
        char c = peek();
        switch (c) {
            case '{': return parse_object();
            case '[': return parse_array();
            case '"': return parse_string();
            case 't': case 'f': return parse_bool();
            case 'n': return parse_null();
            default:
                if (c == '-' || std::isdigit(c)) return parse_number();
                throw ParseError(std::string("Unexpected character: '") + c + "'", pos_);
        }
    }

    Value parse_object() {
        expect('{');
        Object obj;
        if (peek() == '}') { advance(); return obj; }

        while (true) {
            skip_whitespace();
            std::string key = parse_string_raw();
            expect(':');
            obj[key] = parse_value();
            if (peek() == '}') { advance(); break; }
            expect(',');
        }
        return obj;
    }

    Value parse_array() {
        expect('[');
        Array arr;
        if (peek() == ']') { advance(); return arr; }

        while (true) {
            arr.push_back(parse_value());
            if (peek() == ']') { advance(); break; }
            expect(',');
        }
        return arr;
    }

    Value parse_string() {
        return Value(parse_string_raw());
    }

    std::string parse_string_raw() {
        expect('"');
        std::string result;
        while (pos_ < json_.size()) {
            char c = json_[pos_++];
            if (c == '"') return result;
            if (c == '\\') {
                if (pos_ >= json_.size()) throw ParseError("Unexpected end in string escape", pos_);
                char esc = json_[pos_++];
                switch (esc) {
                    case '"': result += '"'; break;
                    case '\\': result += '\\'; break;
                    case '/': result += '/'; break;
                    case 'b': result += '\b'; break;
                    case 'f': result += '\f'; break;
                    case 'n': result += '\n'; break;
                    case 'r': result += '\r'; break;
                    case 't': result += '\t'; break;
                    case 'u': {
                        // 基本 Unicode 转义（仅 BMP）
                        if (pos_ + 4 > json_.size()) throw ParseError("Unexpected end in unicode escape", pos_);
                        std::string hex(4, ' ');
                        for (int i = 0; i < 4; i++) hex[i] = json_[pos_++];
                        uint16_t codepoint = static_cast<uint16_t>(std::stoul(hex, nullptr, 16));
                        if (codepoint < 0x80) result += static_cast<char>(codepoint);
                        else if (codepoint < 0x800) {
                            result += static_cast<char>(0xC0 | (codepoint >> 6));
                            result += static_cast<char>(0x80 | (codepoint & 0x3F));
                        } else {
                            result += static_cast<char>(0xE0 | (codepoint >> 12));
                            result += static_cast<char>(0x80 | ((codepoint >> 6) & 0x3F));
                            result += static_cast<char>(0x80 | (codepoint & 0x3F));
                        }
                        break;
                    }
                    default:
                        throw ParseError(std::string("Invalid escape: \\") + esc, pos_ - 1);
                }
            } else {
                result += c;
            }
        }
        throw ParseError("Unterminated string", pos_);
    }

    Value parse_number() {
        size_t start = pos_;
        if (peek() == '-') advance();

        if (peek() == '0') { advance(); }
        else {
            while (pos_ < json_.size() && std::isdigit(json_[pos_])) advance();
        }

        if (peek() == '.') {
            advance();
            if (pos_ >= json_.size() || !std::isdigit(json_[pos_]))
                throw ParseError("Invalid number: expected digit after decimal", pos_);
            while (pos_ < json_.size() && std::isdigit(json_[pos_])) advance();
        }

        if (peek() == 'e' || peek() == 'E') {
            advance();
            if (peek() == '+' || peek() == '-') advance();
            if (pos_ >= json_.size() || !std::isdigit(json_[pos_]))
                throw ParseError("Invalid number: expected digit in exponent", pos_);
            while (pos_ < json_.size() && std::isdigit(json_[pos_])) advance();
        }

        std::string num_str(json_.substr(start, pos_ - start));
        return Value(std::stod(num_str));
    }

    Value parse_bool() {
        if (json_.substr(pos_, 4) == "true") { pos_ += 4; return Value(true); }
        if (json_.substr(pos_, 5) == "false") { pos_ += 5; return Value(false); }
        throw ParseError("Expected true or false", pos_);
    }

    Value parse_null() {
        if (json_.substr(pos_, 4) == "null") { pos_ += 4; return Value(nullptr); }
        throw ParseError("Expected null", pos_);
    }
};

// ============================================================================
// 便捷函数
// ============================================================================

inline Value parse(const std::string& json) {
    return Parser::parse(json);
}

inline std::string stringify(const Value& v, int indent = 0) {
    return v.dump(indent);
}

} // namespace qoostore::edge::json
