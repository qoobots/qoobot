/*
 * test_activation_client.c — 激活客户端单元测试
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "qooauth/qooauth_activation_client.h"
#include "qooauth/qooauth_cert_manager.h"

static int tests_run = 0;
static int tests_failed = 0;

#define TEST(name) do { \
    tests_run++; \
    printf("  TEST: %s ... ", name); \
} while(0)

#define PASS() printf("PASS\n")
#define FAIL(msg) do { printf("FAIL: %s\n", msg); tests_failed++; } while(0)
#define ASSERT(cond, msg) do { if (!(cond)) { FAIL(msg); return; } } while(0)
#define ASSERT_OK(err, msg) do { if ((err) != QOOAUTH_OK) { FAIL(msg); return; } } while(0)

static void test_config_validation(void) {
    TEST("activation config validation");
    qooauth_activation_result_t result;

    /* NULL config */
    qooauth_error_t err = qooauth_activation_initiate(NULL, &result);
    ASSERT(err == QOOAUTH_ERR_INVALID_ARG, "should reject NULL config");

    /* Missing required fields */
    qooauth_activation_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    err = qooauth_activation_initiate(&cfg, &result);
    ASSERT(err == QOOAUTH_ERR_INVALID_ARG, "should reject missing auth_server_url");

    cfg.auth_server_url = "https://test.com";
    err = qooauth_activation_initiate(&cfg, &result);
    ASSERT(err == QOOAUTH_ERR_INVALID_ARG, "should reject missing device_serial");
    PASS();
}

static void test_challenge_validation(void) {
    TEST("challenge request validation");
    qooauth_activation_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.auth_server_url = "https://test.com";

    qooauth_challenge_t challenge;
    qooauth_error_t err = qooauth_activation_request_challenge(&cfg, NULL, &challenge);
    ASSERT(err == QOOAUTH_ERR_INVALID_ARG, "should reject NULL activation_id");
    PASS();
}

static void test_verify_validation(void) {
    TEST("verify request validation");
    qooauth_activation_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.auth_server_url = "https://test.com";

    qooauth_challenge_t challenge;
    memset(&challenge, 0, sizeof(challenge));

    qooauth_activation_result_t result;
    qooauth_error_t err = qooauth_activation_verify(&cfg, "act_test", &challenge, &result);
    ASSERT(err == QOOAUTH_ERR_INVALID_ARG, "should reject missing bootstrap_key_pem");
    PASS();
}

static void test_result_struct_size(void) {
    TEST("result struct sizes");
    /* Ensure structs fit within reasonable stack limits */
    ASSERT(sizeof(qooauth_activation_result_t) < 16384, "result struct too large");
    ASSERT(sizeof(qooauth_challenge_t) < 1024, "challenge struct too large");
    ASSERT(sizeof(qooauth_activation_config_t) < 1024, "config struct too large");
    PASS();
}

static void test_run_validation(void) {
    TEST("activation_run config validation");
    qooauth_error_t err = qooauth_activation_run(NULL, NULL);
    ASSERT(err == QOOAUTH_ERR_INVALID_ARG, "should reject NULL");
    PASS();
}

int main(void) {
    printf("=== QooAuth Activation Client Tests ===\n\n");

    test_config_validation();
    test_challenge_validation();
    test_verify_validation();
    test_result_struct_size();
    test_run_validation();

    printf("\n=== Results: %d/%d passed, %d failed ===\n",
           tests_run - tests_failed, tests_run, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}
