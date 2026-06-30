/*
 * qooauth_activation_client.c — 设备激活客户端实现
 *
 * Implements the 3-step activation protocol:
 *   1. Initiate: POST device info → server creates activation session
 *   2. Challenge: GET cryptographic challenge (nonce)
 *   3. Verify: POST signed nonce → server issues operational certificate
 */
#include "qooauth/qooauth_activation_client.h"
#include "qooauth/qooauth_cert_manager.h"
#include "qooauth/qooauth_internal.h"

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>

#include <json-c/json.h>
#include <curl/curl.h>

#include <mbedtls/pk.h>
#include <mbedtls/ecdsa.h>
#include <mbedtls/sha256.h>
#include <mbedtls/ctr_drbg.h>
#include <mbedtls/entropy.h>
#include <mbedtls/base64.h>
#include <mbedtls/error.h>
#include <mbedtls/pem.h>

/* ========================================================================
 * HTTP response buffer
 * ======================================================================== */

struct http_response {
    uint8_t* data;
    size_t   len;
    size_t   cap;
    long     http_status;
};

static size_t curl_write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t realsize = size * nmemb;
    struct http_response* resp = (struct http_response*)userp;

    if (resp->len + realsize + 1 > resp->cap) {
        size_t new_cap = (resp->cap * 2 > resp->len + realsize + 1)
                         ? resp->cap * 2 : resp->len + realsize + 1;
        if (new_cap > QOOAUTH_MAX_HTTP_BODY) return 0;
        uint8_t* new_data = (uint8_t*)realloc(resp->data, new_cap);
        if (!new_data) return 0;
        resp->data = new_data;
        resp->cap = new_cap;
    }

    memcpy(resp->data + resp->len, contents, realsize);
    resp->len += realsize;
    resp->data[resp->len] = '\0';
    return realsize;
}

/* ========================================================================
 * JSON helpers
 * ======================================================================== */

static int json_get_string(json_object* obj, const char* key,
                            char* out, size_t out_size) {
    json_object* val;
    if (!json_object_object_get_ex(obj, key, &val)) return -1;
    const char* str = json_object_get_string(val);
    if (!str) return -1;
    qooauth_strncpy_safe(out, str, out_size);
    return 0;
}

static int json_get_int64(json_object* obj, const char* key, int64_t* out) {
    json_object* val;
    if (!json_object_object_get_ex(obj, key, &val)) return -1;
    *out = json_object_get_int64(val);
    return 0;
}

static int json_get_bool(json_object* obj, const char* key, int* out) {
    json_object* val;
    if (!json_object_object_get_ex(obj, key, &val)) return -1;
    *out = json_object_get_boolean(val);
    return 0;
}

/* ========================================================================
 * HTTP POST helper
 * ======================================================================== */

static qooauth_error_t http_post_json(
    const char* url, const char* json_body,
    struct http_response* resp, uint32_t timeout_s)
{
    CURL* curl = curl_easy_init();
    if (!curl) return QOOAUTH_ERR_ACTIVATION_HTTP;

    struct curl_slist* headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    headers = curl_slist_append(headers, "Accept: application/json");

    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json_body);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, (long)strlen(json_body));
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, resp);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, (long)(timeout_s ? timeout_s : QOOAUTH_DEFAULT_ACTIVATION_TIMEOUT_S));
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 2L);

    CURLcode res = curl_easy_perform(curl);
    if (res != CURLE_OK) {
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
        return QOOAUTH_ERR_ACTIVATION_HTTP;
    }

    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &resp->http_status);
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    return QOOAUTH_OK;
}

/* ========================================================================
 * ECDSA signature for challenge verification
 * ======================================================================== */

static qooauth_error_t sign_challenge_nonce(
    const char* key_pem, size_t key_len,
    const uint8_t* nonce, size_t nonce_len,
    char* out_sig_b64, size_t sig_buf_size)
{
    mbedtls_pk_context pk;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context drbg;

    mbedtls_pk_init(&pk);
    mbedtls_entropy_init(&entropy);
    mbedtls_ctr_drbg_init(&drbg);

    int ret = mbedtls_ctr_drbg_seed(&drbg, mbedtls_entropy_func, &entropy, NULL, 0);
    if (ret != 0) goto error;

    ret = mbedtls_pk_parse_key(&pk, (const uint8_t*)key_pem, key_len + 1,
                                NULL, 0, mbedtls_ctr_drbg_random, &drbg);
    if (ret != 0) goto error;

    /* Hash the nonce with SHA-256 before signing */
    uint8_t hash[32];
    mbedtls_sha256(nonce, nonce_len, hash, 0);

    /* Sign */
    uint8_t sig[MBEDTLS_ECDSA_MAX_LEN];
    size_t sig_len;
    ret = mbedtls_pk_sign(&pk, MBEDTLS_MD_SHA256,
                           hash, 32, sig, sizeof(sig), &sig_len,
                           mbedtls_ctr_drbg_random, &drbg);
    if (ret != 0) goto error;

    /* Base64-encode the signature */
    size_t b64_len;
    ret = mbedtls_base64_encode((uint8_t*)out_sig_b64, sig_buf_size,
                                 &b64_len, sig, sig_len);
    if (ret != 0) goto error;
    out_sig_b64[b64_len] = '\0';

    mbedtls_pk_free(&pk);
    mbedtls_ctr_drbg_free(&drbg);
    mbedtls_entropy_free(&entropy);
    return QOOAUTH_OK;

error:
    mbedtls_pk_free(&pk);
    mbedtls_ctr_drbg_free(&drbg);
    mbedtls_entropy_free(&entropy);
    return QOOAUTH_ERR_ACTIVATION_VERIFY;
}

/* ========================================================================
 * Public API
 * ======================================================================== */

qooauth_error_t qooauth_activation_initiate(
    const qooauth_activation_config_t* config,
    qooauth_activation_result_t* out)
{
    if (!config || !out) return QOOAUTH_ERR_INVALID_ARG;
    if (!config->auth_server_url || !config->device_serial
        || !config->bootstrap_cert_pem)
        return QOOAUTH_ERR_INVALID_ARG;

    memset(out, 0, sizeof(*out));

    /* Build JSON body */
    json_object* body = json_object_new_object();
    json_object_object_add(body, "device_serial",
        json_object_new_string(config->device_serial));
    json_object_object_add(body, "hardware_model",
        json_object_new_string(config->hardware_model ? config->hardware_model : "unknown"));
    json_object_object_add(body, "bootstrap_cert_pem",
        json_object_new_string(config->bootstrap_cert_pem));

    const char* json_str = json_object_to_json_string(body);

    /* Build URL */
    char url[QOOAUTH_MAX_URL_LEN];
    snprintf(url, sizeof(url), "%s/api/v1/auth/device-activations/initiate",
             config->auth_server_url);

    /* Send request */
    struct http_response resp = {0};
    resp.data = (uint8_t*)malloc(4096);
    if (!resp.data) { json_object_put(body); return QOOAUTH_ERR_OUT_OF_MEMORY; }
    resp.cap = 4096;

    qooauth_error_t err = http_post_json(url, json_str, &resp, config->timeout_seconds);
    json_object_put(body);

    if (err != QOOAUTH_OK) { free(resp.data); return err; }

    /* Parse response */
    json_object* root = json_tokener_parse((const char*)resp.data);
    if (!root) { free(resp.data); return QOOAUTH_ERR_ACTIVATION_JSON; }

    json_get_bool(root, "success", &out->success);
    if (!out->success) {
        json_get_string(root, "error_code", out->error_code, sizeof(out->error_code));
        json_get_string(root, "error", out->error_message, sizeof(out->error_message));
        json_object_put(root);
        free(resp.data);
        return QOOAUTH_ERR_ACTIVATION_REJECTED;
    }

    json_object* data;
    if (json_object_object_get_ex(root, "data", &data)) {
        json_get_string(data, "activation_id", out->activation_id, sizeof(out->activation_id));
        json_get_int64(data, "expires_at", &out->expires_at);
    }

    json_object_put(root);
    free(resp.data);
    return QOOAUTH_OK;
}

qooauth_error_t qooauth_activation_request_challenge(
    const qooauth_activation_config_t* config,
    const char* activation_id,
    qooauth_challenge_t* out)
{
    if (!config || !activation_id || !out) return QOOAUTH_ERR_INVALID_ARG;

    memset(out, 0, sizeof(*out));

    char url[QOOAUTH_MAX_URL_LEN];
    snprintf(url, sizeof(url),
             "%s/api/v1/auth/device-activations/%s/challenge",
             config->auth_server_url, activation_id);

    struct http_response resp = {0};
    resp.data = (uint8_t*)malloc(4096);
    if (!resp.data) return QOOAUTH_ERR_OUT_OF_MEMORY;
    resp.cap = 4096;

    /* POST with empty JSON body */
    qooauth_error_t err = http_post_json(url, "{}", &resp, config->timeout_seconds);
    if (err != QOOAUTH_OK) { free(resp.data); return err; }

    json_object* root = json_tokener_parse((const char*)resp.data);
    if (!root) { free(resp.data); return QOOAUTH_ERR_ACTIVATION_JSON; }

    int success = 0;
    json_get_bool(root, "success", &success);
    if (!success) {
        json_object_put(root);
        free(resp.data);
        return QOOAUTH_ERR_ACTIVATION_CHALLENGE;
    }

    json_object* data;
    if (json_object_object_get_ex(root, "data", &data)) {
        json_get_string(data, "nonce_hex", out->nonce_hex, sizeof(out->nonce_hex));
        json_get_string(data, "algorithm", out->algorithm, sizeof(out->algorithm));
        json_get_int64(data, "expires_at", &out->expires_at);
    }
    qooauth_strncpy_safe(out->activation_id, activation_id, sizeof(out->activation_id));

    json_object_put(root);
    free(resp.data);
    return QOOAUTH_OK;
}

qooauth_error_t qooauth_activation_verify(
    const qooauth_activation_config_t* config,
    const char* activation_id,
    const qooauth_challenge_t* challenge,
    qooauth_activation_result_t* out)
{
    if (!config || !activation_id || !challenge || !out)
        return QOOAUTH_ERR_INVALID_ARG;
    if (!config->bootstrap_key_pem)
        return QOOAUTH_ERR_INVALID_ARG;

    memset(out, 0, sizeof(*out));

    /* Decode nonce from hex */
    uint8_t nonce[QOOAUTH_NONCE_LEN];
    int nonce_len = qooauth_hex2bin(challenge->nonce_hex, nonce, sizeof(nonce));
    if (nonce_len < 0) return QOOAUTH_ERR_ACTIVATION_CHALLENGE;

    /* Sign the nonce */
    char sig_b64[256];
    qooauth_error_t err = sign_challenge_nonce(
        config->bootstrap_key_pem, strlen(config->bootstrap_key_pem),
        nonce, (size_t)nonce_len, sig_b64, sizeof(sig_b64));
    qooauth_secure_zero(nonce, sizeof(nonce));
    if (err != QOOAUTH_OK) return err;

    /* Build JSON body */
    json_object* body = json_object_new_object();
    json_object_object_add(body, "nonce_hex",
        json_object_new_string(challenge->nonce_hex));
    json_object_object_add(body, "signature",
        json_object_new_string(sig_b64));
    json_object_object_add(body, "algorithm",
        json_object_new_string("ECDSA_P256_SHA256"));

    const char* json_str = json_object_to_json_string(body);

    char url[QOOAUTH_MAX_URL_LEN];
    snprintf(url, sizeof(url),
             "%s/api/v1/auth/device-activations/%s/verify",
             config->auth_server_url, activation_id);

    struct http_response resp = {0};
    resp.data = (uint8_t*)malloc(QOOAUTH_MAX_CERT_PEM);
    if (!resp.data) { json_object_put(body); return QOOAUTH_ERR_OUT_OF_MEMORY; }
    resp.cap = QOOAUTH_MAX_CERT_PEM;

    err = http_post_json(url, json_str, &resp, config->timeout_seconds);
    json_object_put(body);

    if (err != QOOAUTH_OK) { free(resp.data); return err; }

    json_object* root = json_tokener_parse((const char*)resp.data);
    if (!root) { free(resp.data); return QOOAUTH_ERR_ACTIVATION_JSON; }

    json_get_bool(root, "success", &out->success);
    if (!out->success) {
        json_get_string(root, "error_code", out->error_code, sizeof(out->error_code));
        json_get_string(root, "error", out->error_message, sizeof(out->error_message));
        json_object_put(root);
        free(resp.data);
        return QOOAUTH_ERR_ACTIVATION_VERIFY;
    }

    json_object* data;
    if (json_object_object_get_ex(root, "data", &data)) {
        json_get_string(data, "device_id", out->device_id, sizeof(out->device_id));
        json_get_string(data, "cert_pem", out->cert_pem, sizeof(out->cert_pem));
        json_get_string(data, "cert_id", out->cert_id, sizeof(out->cert_id));
        json_get_string(data, "binding_token", out->binding_token, sizeof(out->binding_token));
        json_get_int64(data, "expires_at", &out->expires_at);
    }

    json_object_put(root);
    free(resp.data);
    return QOOAUTH_OK;
}

qooauth_error_t qooauth_activation_run(
    const qooauth_activation_config_t* config,
    qooauth_activation_result_t* out)
{
    if (!config || !out) return QOOAUTH_ERR_INVALID_ARG;

    memset(out, 0, sizeof(*out));

    int attempts = 0;
    qooauth_error_t err;

    /* Step 1: Initiate */
    err = qooauth_activation_initiate(config, out);
    if (err != QOOAUTH_OK) return err;

    /* Step 2: Request challenge */
    qooauth_challenge_t challenge;
    err = qooauth_activation_request_challenge(config, out->activation_id, &challenge);
    if (err != QOOAUTH_OK) return err;

    /* Step 3: Verify with retry */
    for (attempts = 0; attempts < QOOAUTH_MAX_ACTIVATION_ATTEMPTS; attempts++) {
        err = qooauth_activation_verify(config, out->activation_id, &challenge, out);
        if (err == QOOAUTH_OK && out->success) {
            return QOOAUTH_OK;
        }
        if (err == QOOAUTH_ERR_ACTIVATION_VERIFY) {
            /* Transient failure — retry with new challenge */
            err = qooauth_activation_request_challenge(config, out->activation_id, &challenge);
            if (err != QOOAUTH_OK) return err;
            continue;
        }
        break;
    }

    if (attempts >= QOOAUTH_MAX_ACTIVATION_ATTEMPTS) {
        return QOOAUTH_ERR_ACTIVATION_MAX_ATTEMPTS;
    }

    return err;
}

qooauth_error_t qooauth_activation_revoke(
    const qooauth_activation_config_t* config,
    const char* device_id, const char* cert_id, const char* reason)
{
    if (!config || !device_id) return QOOAUTH_ERR_INVALID_ARG;

    json_object* body = json_object_new_object();
    json_object_object_add(body, "device_id", json_object_new_string(device_id));
    if (cert_id) json_object_object_add(body, "cert_id", json_object_new_string(cert_id));
    json_object_object_add(body, "reason",
        json_object_new_string(reason ? reason : "user_requested"));

    const char* json_str = json_object_to_json_string(body);

    char url[QOOAUTH_MAX_URL_LEN];
    snprintf(url, sizeof(url),
             "%s/api/v1/auth/device-activations/%s/revoke",
             config->auth_server_url, device_id);

    struct http_response resp = {0};
    resp.data = (uint8_t*)malloc(4096);
    if (!resp.data) { json_object_put(body); return QOOAUTH_ERR_OUT_OF_MEMORY; }
    resp.cap = 4096;

    qooauth_error_t err = http_post_json(url, json_str, &resp, config->timeout_seconds);
    json_object_put(body);
    free(resp.data);

    return err;
}
