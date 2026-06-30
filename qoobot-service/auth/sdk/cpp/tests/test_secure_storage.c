/*
 * test_secure_storage.c — 安全存储单元测试
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "qooauth/qooauth_secure_storage.h"

static int tests_run = 0;
static int tests_failed = 0;

#define TEST(name) do { \
    tests_run++; \
    printf("  TEST: %s ... ", name); \
} while(0)

#define PASS() printf("PASS\n")
#define FAIL(msg) do { \
    printf("FAIL: %s\n", msg); \
    tests_failed++; \
} while(0)

#define ASSERT(cond, msg) do { \
    if (!(cond)) { FAIL(msg); return; } \
} while(0)

#define ASSERT_OK(err, msg) do { \
    if ((err) != QOOAUTH_OK) { FAIL(msg); return; } \
} while(0)

/* Test encryption key */
static const uint8_t test_key[32] = {
    0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,
    0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f,
    0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17,
    0x18,0x19,0x1a,0x1b,0x1c,0x1d,0x1e,0x1f,
};

static void test_init_destroy(void) {
    TEST("init/destroy");
    qooauth_storage_t* s = NULL;
    qooauth_error_t err = qooauth_storage_init("/tmp/qooauth_test", test_key, 32, &s);
    ASSERT_OK(err, "init failed");
    ASSERT(s != NULL, "handle is NULL");
    qooauth_storage_destroy(s);
    PASS();
}

static void test_store_load_key(void) {
    TEST("store/load key");
    qooauth_storage_t* s = NULL;
    qooauth_storage_init("/tmp/qooauth_test", test_key, 32, &s);

    const char* key_pem = "-----BEGIN EC PRIVATE KEY-----\n"
                          "MHcCAQEEIAbc1234...test_key_data...\n"
                          "-----END EC PRIVATE KEY-----\n";

    qooauth_error_t err = qooauth_storage_store_key(s, "dev_test", key_pem, strlen(key_pem));
    ASSERT_OK(err, "store key failed");

    char loaded[4096];
    size_t loaded_len;
    err = qooauth_storage_load_key(s, "dev_test", loaded, sizeof(loaded), &loaded_len);
    ASSERT_OK(err, "load key failed");
    ASSERT(strcmp(loaded, key_pem) == 0, "key mismatch");

    qooauth_storage_destroy(s);
    PASS();
}

static void test_store_load_cert(void) {
    TEST("store/load certificate");
    qooauth_storage_t* s = NULL;
    qooauth_storage_init("/tmp/qooauth_test", test_key, 32, &s);

    const char* cert = "-----BEGIN CERTIFICATE-----\n"
                       "MIIB...test_cert...\n"
                       "-----END CERTIFICATE-----\n";

    qooauth_error_t err = qooauth_storage_store_cert(s, "dev_test", cert, strlen(cert));
    ASSERT_OK(err, "store cert failed");

    char loaded[8192];
    size_t loaded_len;
    err = qooauth_storage_load_cert(s, "dev_test", loaded, sizeof(loaded), &loaded_len);
    ASSERT_OK(err, "load cert failed");
    ASSERT(strcmp(loaded, cert) == 0, "cert mismatch");

    qooauth_storage_destroy(s);
    PASS();
}

static void test_has_credentials(void) {
    TEST("has_credentials");
    qooauth_storage_t* s = NULL;
    qooauth_storage_init("/tmp/qooauth_test", test_key, 32, &s);

    ASSERT(qooauth_storage_has_credentials(s, "nonexistent") == 0, "should not have creds");

    /* Store key and cert */
    qooauth_storage_store_key(s, "dev_has", "key", 3);
    qooauth_storage_store_cert(s, "dev_has", "cert", 4);

    ASSERT(qooauth_storage_has_credentials(s, "dev_has") == 1, "should have creds");

    qooauth_storage_destroy(s);
    PASS();
}

static void test_delete_key(void) {
    TEST("delete key");
    qooauth_storage_t* s = NULL;
    qooauth_storage_init("/tmp/qooauth_test", test_key, 32, &s);

    qooauth_storage_store_key(s, "dev_del", "secret_key", 10);
    ASSERT(qooauth_storage_has_credentials(s, "dev_del") == 0, "should not have cert");

    qooauth_error_t err = qooauth_storage_delete_key(s, "dev_del");
    ASSERT_OK(err, "delete failed");

    char buf[1024];
    err = qooauth_storage_load_key(s, "dev_del", buf, sizeof(buf), NULL);
    ASSERT(err == QOOAUTH_ERR_STORAGE_NOT_FOUND, "key should be gone");

    qooauth_storage_destroy(s);
    PASS();
}

int main(void) {
    printf("=== QooAuth Secure Storage Tests ===\n\n");

    test_init_destroy();
    test_store_load_key();
    test_store_load_cert();
    test_has_credentials();
    test_delete_key();

    printf("\n=== Results: %d/%d passed, %d failed ===\n",
           tests_run - tests_failed, tests_run, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}
