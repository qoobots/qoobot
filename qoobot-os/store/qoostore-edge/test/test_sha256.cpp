/**
 * test_sha256.cpp — SHA-256 哈希工具单元测试
 *
 * 测试向量来自 NIST SHA-256 标准测试用例。
 */

#include "sha256.hpp"
#include <string>

using namespace qoostore::edge::crypto;

TEST(sha256_empty_string) {
    // SHA-256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    std::string expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
    auto digest = SHA256::hash("");
    std::string hex = SHA256::hex(digest);
    CHECK_EQ(hex, expected);
    return true;
}

TEST(sha256_abc) {
    // SHA-256("abc") = ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
    std::string expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
    auto digest = SHA256::hash("abc");
    std::string hex = SHA256::hex(digest);
    CHECK_EQ(hex, expected);
    return true;
}

TEST(sha256_long_string) {
    // SHA-256("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq")
    std::string input = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
    std::string expected = "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1";
    auto digest = SHA256::hash(input);
    std::string hex = SHA256::hex(digest);
    CHECK_EQ(hex, expected);
    return true;
}

TEST(sha256_digest_size) {
    auto digest = SHA256::hash("test");
    CHECK_EQ(digest.size(), SHA256::DIGEST_SIZE);
    CHECK_EQ(digest.size(), 32u);
    return true;
}

TEST(sha256_hex_length) {
    std::string hex = SHA256::hex("hello world");
    CHECK_EQ(hex.length(), 64u);
    return true;
}

TEST(sha256_deterministic) {
    auto d1 = SHA256::hash("test data");
    auto d2 = SHA256::hash("test data");
    CHECK_EQ(SHA256::hex(d1), SHA256::hex(d2));
    return true;
}

TEST(sha256_different_inputs) {
    auto d1 = SHA256::hex("hello");
    auto d2 = SHA256::hex("world");
    CHECK(d1 != d2);
    return true;
}

TEST(sha256_incremental_update) {
    // 增量更新应该和一次性哈希产生相同结果
    SHA256 incremental;
    incremental.update("hel");
    incremental.update("lo wo");
    incremental.update("rld");
    auto d1 = incremental.finalize();

    auto d2 = SHA256::hash("hello world");
    CHECK_EQ(SHA256::hex(d1), SHA256::hex(d2));
    return true;
}

TEST(sha256_reset) {
    SHA256 s;
    s.update("test1");
    auto d1 = s.finalize();

    s.reset();
    s.update("test2");
    auto d2 = s.finalize();

    CHECK(SHA256::hex(d1) != SHA256::hex(d2));
    return true;
}

TEST(sha256_hex_static) {
    std::string hex = SHA256::hex("data");
    CHECK_EQ(hex.length(), 64u);
    // 验证全部是十六进制字符
    for (char c : hex) {
        CHECK((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'));
    }
    return true;
}

TEST(sha256_key_fingerprint) {
    std::string key = "test_public_key_data";
    std::string fingerprint = compute_key_fingerprint(key);
    CHECK(fingerprint.starts_with("SHA256:"));
    CHECK_EQ(fingerprint.length(), 7 + 64); // "SHA256:" + 64 hex chars
    return true;
}
