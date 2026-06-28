/*
 * qooauth_secure_storage.c — 安全存储实现
 *
 * Storage layout:
 *   {root}/keys/{device_id}.enc    — AES-256-GCM encrypted private key
 *   {root}/certs/{device_id}.pem   — Device certificate (plaintext)
 *   {root}/certs/ca_bundle.pem     — CA bundle
 *   {root}/state/{device_id}.json  — Device state
 */
#include "qooauth/qooauth_secure_storage.h"
#include "qooauth/qooauth_internal.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>

#ifdef _WIN32
#include <direct.h>
#define mkdir_p(path) _mkdir(path)
#else
#include <unistd.h>
#define mkdir_p(path) mkdir(path, 0700)
#endif

/* ========================================================================
 * Internal structure
 * ======================================================================== */

struct qooauth_storage {
    char     root[512];
    uint8_t  aes_key[QOOAUTH_AES_KEY_LEN];
    int      key_set;
};

/* Forward declaration for AES-GCM (uses mbedTLS) */
#include <mbedtls/gcm.h>
#include <mbedtls/entropy.h>
#include <mbedtls/ctr_drbg.h>

/* ========================================================================
 * Path helpers
 * ======================================================================== */

static int ensure_dir(const char* path) {
    struct stat st;
    if (stat(path, &st) == 0) {
        return S_ISDIR(st.st_mode) ? 0 : -1;
    }
    return mkdir_p(path);
}

static int build_path(const qooauth_storage_t* s, const char* subdir,
                       const char* filename, char* out, size_t out_size) {
    return snprintf(out, out_size, "%s/%s/%s", s->root, subdir, filename);
}

/* ========================================================================
 * AES-256-GCM encrypt/decrypt
 * ======================================================================== */

static qooauth_error_t aes_gcm_encrypt(
    const uint8_t* key, const uint8_t* plaintext, size_t pt_len,
    uint8_t* out_ciphertext, size_t* out_ct_len)
{
    mbedtls_gcm_context ctx;
    mbedtls_gcm_init(&ctx);

    uint8_t iv[QOOAUTH_AES_IV_LEN];
    uint8_t tag[QOOAUTH_AES_TAG_LEN];

    /* Generate random IV */
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context drbg;
    mbedtls_entropy_init(&entropy);
    mbedtls_ctr_drbg_init(&drbg);
    mbedtls_ctr_drbg_seed(&drbg, mbedtls_entropy_func, &entropy, NULL, 0);
    mbedtls_ctr_drbg_random(&drbg, iv, QOOAUTH_AES_IV_LEN);

    int ret = mbedtls_gcm_setkey(&ctx, MBEDTLS_CIPHER_ID_AES, key, 256);
    if (ret != 0) {
        mbedtls_gcm_free(&ctx);
        mbedtls_ctr_drbg_free(&drbg);
        mbedtls_entropy_free(&entropy);
        return QOOAUTH_ERR_STORAGE_WRITE;
    }

    ret = mbedtls_gcm_crypt_and_tag(&ctx, MBEDTLS_GCM_ENCRYPT,
                                     pt_len, iv, QOOAUTH_AES_IV_LEN,
                                     NULL, 0, plaintext, out_ciphertext + QOOAUTH_AES_IV_LEN + QOOAUTH_AES_TAG_LEN,
                                     QOOAUTH_AES_TAG_LEN, tag);
    if (ret != 0) {
        mbedtls_gcm_free(&ctx);
        mbedtls_ctr_drbg_free(&drbg);
        mbedtls_entropy_free(&entropy);
        return QOOAUTH_ERR_STORAGE_WRITE;
    }

    /* Format: [IV (12)] [TAG (16)] [CIPHERTEXT] */
    memcpy(out_ciphertext, iv, QOOAUTH_AES_IV_LEN);
    memcpy(out_ciphertext + QOOAUTH_AES_IV_LEN, tag, QOOAUTH_AES_TAG_LEN);
    *out_ct_len = QOOAUTH_AES_IV_LEN + QOOAUTH_AES_TAG_LEN + pt_len;

    mbedtls_gcm_free(&ctx);
    mbedtls_ctr_drbg_free(&drbg);
    mbedtls_entropy_free(&entropy);
    return QOOAUTH_OK;
}

static qooauth_error_t aes_gcm_decrypt(
    const uint8_t* key, const uint8_t* ciphertext, size_t ct_len,
    uint8_t* out_plaintext, size_t* out_pt_len)
{
    if (ct_len < QOOAUTH_AES_IV_LEN + QOOAUTH_AES_TAG_LEN) {
        return QOOAUTH_ERR_STORAGE_INTEGRITY;
    }

    mbedtls_gcm_context ctx;
    mbedtls_gcm_init(&ctx);

    const uint8_t* iv  = ciphertext;
    const uint8_t* tag = ciphertext + QOOAUTH_AES_IV_LEN;
    const uint8_t* ct  = ciphertext + QOOAUTH_AES_IV_LEN + QOOAUTH_AES_TAG_LEN;
    size_t pt_len = ct_len - QOOAUTH_AES_IV_LEN - QOOAUTH_AES_TAG_LEN;

    int ret = mbedtls_gcm_setkey(&ctx, MBEDTLS_CIPHER_ID_AES, key, 256);
    if (ret != 0) {
        mbedtls_gcm_free(&ctx);
        return QOOAUTH_ERR_STORAGE_INTEGRITY;
    }

    ret = mbedtls_gcm_auth_decrypt(&ctx, pt_len,
                                    iv, QOOAUTH_AES_IV_LEN,
                                    NULL, 0,
                                    tag, QOOAUTH_AES_TAG_LEN,
                                    ct, out_plaintext);
    mbedtls_gcm_free(&ctx);

    if (ret != 0) {
        return QOOAUTH_ERR_STORAGE_INTEGRITY;
    }

    *out_pt_len = pt_len;
    return QOOAUTH_OK;
}

/* ========================================================================
 * File I/O helpers
 * ======================================================================== */

static qooauth_error_t read_file(const char* path, uint8_t* buf, size_t buf_size, size_t* out_len) {
    FILE* f = fopen(path, "rb");
    if (!f) return QOOAUTH_ERR_STORAGE_NOT_FOUND;

    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (fsize < 0 || (size_t)fsize > buf_size) {
        fclose(f);
        return (fsize < 0) ? QOOAUTH_ERR_STORAGE_READ : QOOAUTH_ERR_BUFFER_TOO_SMALL;
    }

    size_t nread = fread(buf, 1, (size_t)fsize, f);
    fclose(f);

    if (nread != (size_t)fsize) return QOOAUTH_ERR_STORAGE_READ;
    if (out_len) *out_len = nread;
    return QOOAUTH_OK;
}

static qooauth_error_t write_file(const char* path, const uint8_t* data, size_t len) {
    FILE* f = fopen(path, "wb");
    if (!f) return QOOAUTH_ERR_STORAGE_WRITE;

    size_t written = fwrite(data, 1, len, f);
    fclose(f);

    if (written != len) return QOOAUTH_ERR_STORAGE_WRITE;

    /* Set restrictive permissions on Unix */
#ifndef _WIN32
    chmod(path, 0600);
#endif
    return QOOAUTH_OK;
}

/* ========================================================================
 * Public API
 * ======================================================================== */

qooauth_error_t qooauth_storage_init(
    const char* storage_root, const uint8_t* platform_key,
    size_t key_len, qooauth_storage_t** out)
{
    if (!out) return QOOAUTH_ERR_INVALID_ARG;

    qooauth_storage_t* s = (qooauth_storage_t*)calloc(1, sizeof(*s));
    if (!s) return QOOAUTH_ERR_OUT_OF_MEMORY;

    /* Determine storage root */
    if (storage_root) {
        qooauth_strncpy_safe(s->root, storage_root, sizeof(s->root));
    } else {
#ifdef _WIN32
        const char* home = getenv("USERPROFILE");
        if (!home) home = "C:\\qooauth";
        snprintf(s->root, sizeof(s->root), "%s\\.qoobot", home);
#else
        const char* home = getenv("HOME");
        if (!home) home = "/tmp";
        snprintf(s->root, sizeof(s->root), "%s/.qoobot", home);
#endif
    }

    /* Create directory structure */
    char subdir[640];
    snprintf(subdir, sizeof(subdir), "%s/keys", s->root);
    if (ensure_dir(subdir) != 0) { free(s); return QOOAUTH_ERR_STORAGE_OPEN; }
    snprintf(subdir, sizeof(subdir), "%s/certs", s->root);
    if (ensure_dir(subdir) != 0) { free(s); return QOOAUTH_ERR_STORAGE_OPEN; }
    snprintf(subdir, sizeof(subdir), "%s/state", s->root);
    if (ensure_dir(subdir) != 0) { free(s); return QOOAUTH_ERR_STORAGE_OPEN; }

    /* Store encryption key */
    if (platform_key && key_len == QOOAUTH_AES_KEY_LEN) {
        memcpy(s->aes_key, platform_key, QOOAUTH_AES_KEY_LEN);
        s->key_set = 1;
    }

    *out = s;
    return QOOAUTH_OK;
}

void qooauth_storage_destroy(qooauth_storage_t* s) {
    if (s) {
        qooauth_secure_zero(s->aes_key, sizeof(s->aes_key));
        free(s);
    }
}

/* ---- Key storage ---- */

qooauth_error_t qooauth_storage_store_key(
    qooauth_storage_t* s, const char* device_id,
    const char* key_pem, size_t key_len)
{
    if (!s || !device_id || !key_pem) return QOOAUTH_ERR_INVALID_ARG;
    if (!s->key_set) return QOOAUTH_ERR_STORAGE_LOCKED;

    char path[640];
    build_path(s, "keys", device_id, path, sizeof(path));

    uint8_t encrypted[QOOAUTH_MAX_KEY_PEM + QOOAUTH_AES_IV_LEN + QOOAUTH_AES_TAG_LEN];
    size_t enc_len;
    qooauth_error_t err = aes_gcm_encrypt(s->aes_key, (const uint8_t*)key_pem, key_len,
                                           encrypted, &enc_len);
    if (err != QOOAUTH_OK) return err;

    return write_file(path, encrypted, enc_len);
}

qooauth_error_t qooauth_storage_load_key(
    qooauth_storage_t* s, const char* device_id,
    char* out_buf, size_t buf_size, size_t* out_len)
{
    if (!s || !device_id || !out_buf) return QOOAUTH_ERR_INVALID_ARG;
    if (!s->key_set) return QOOAUTH_ERR_STORAGE_LOCKED;

    char path[640];
    build_path(s, "keys", device_id, path, sizeof(path));

    uint8_t encrypted[QOOAUTH_MAX_KEY_PEM + QOOAUTH_AES_IV_LEN + QOOAUTH_AES_TAG_LEN];
    size_t enc_len;
    qooauth_error_t err = read_file(path, encrypted, sizeof(encrypted), &enc_len);
    if (err != QOOAUTH_OK) return err;

    uint8_t plaintext[QOOAUTH_MAX_KEY_PEM];
    size_t pt_len;
    err = aes_gcm_decrypt(s->aes_key, encrypted, enc_len, plaintext, &pt_len);
    if (err != QOOAUTH_OK) return err;

    if (pt_len >= buf_size) return QOOAUTH_ERR_BUFFER_TOO_SMALL;
    memcpy(out_buf, plaintext, pt_len);
    out_buf[pt_len] = '\0';
    qooauth_secure_zero(plaintext, sizeof(plaintext));

    if (out_len) *out_len = pt_len;
    return QOOAUTH_OK;
}

qooauth_error_t qooauth_storage_delete_key(qooauth_storage_t* s, const char* device_id) {
    if (!s || !device_id) return QOOAUTH_ERR_INVALID_ARG;

    char path[640];
    build_path(s, "keys", device_id, path, sizeof(path));

    /* Secure overwrite before delete */
    struct stat st;
    if (stat(path, &st) == 0 && st.st_size > 0) {
        size_t fsize = (size_t)st.st_size;
        if (fsize < 1024 * 1024) {
            uint8_t* zeros = (uint8_t*)calloc(1, fsize);
            if (zeros) {
                FILE* f = fopen(path, "wb");
                if (f) { fwrite(zeros, 1, fsize, f); fclose(f); }
                free(zeros);
            }
        }
    }

    if (remove(path) != 0 && errno != ENOENT) {
        return QOOAUTH_ERR_STORAGE_WRITE;
    }
    return QOOAUTH_OK;
}

/* ---- Certificate storage ---- */

qooauth_error_t qooauth_storage_store_cert(
    qooauth_storage_t* s, const char* device_id,
    const char* cert_pem, size_t cert_len)
{
    if (!s || !device_id || !cert_pem) return QOOAUTH_ERR_INVALID_ARG;

    char path[640];
    build_path(s, "certs", device_id, path, sizeof(path));
    return write_file(path, (const uint8_t*)cert_pem, cert_len);
}

qooauth_error_t qooauth_storage_load_cert(
    qooauth_storage_t* s, const char* device_id,
    char* out_buf, size_t buf_size, size_t* out_len)
{
    if (!s || !device_id || !out_buf) return QOOAUTH_ERR_INVALID_ARG;

    char path[640];
    build_path(s, "certs", device_id, path, sizeof(path));

    size_t len;
    qooauth_error_t err = read_file(path, (uint8_t*)out_buf, buf_size - 1, &len);
    if (err != QOOAUTH_OK) return err;
    out_buf[len] = '\0';
    if (out_len) *out_len = len;
    return QOOAUTH_OK;
}

qooauth_error_t qooauth_storage_store_ca_bundle(
    qooauth_storage_t* s, const char* ca_bundle_pem, size_t ca_bundle_len)
{
    if (!s || !ca_bundle_pem) return QOOAUTH_ERR_INVALID_ARG;

    char path[640];
    build_path(s, "certs", "ca_bundle.pem", path, sizeof(path));
    return write_file(path, (const uint8_t*)ca_bundle_pem, ca_bundle_len);
}

qooauth_error_t qooauth_storage_load_ca_bundle(
    qooauth_storage_t* s, char* out_buf, size_t buf_size, size_t* out_len)
{
    if (!s || !out_buf) return QOOAUTH_ERR_INVALID_ARG;

    char path[640];
    build_path(s, "certs", "ca_bundle.pem", path, sizeof(path));

    size_t len;
    qooauth_error_t err = read_file(path, (uint8_t*)out_buf, buf_size - 1, &len);
    if (err != QOOAUTH_OK) return err;
    out_buf[len] = '\0';
    if (out_len) *out_len = len;
    return QOOAUTH_OK;
}

/* ---- State storage ---- */

qooauth_error_t qooauth_storage_store_state(
    qooauth_storage_t* s, const char* device_id,
    const char* state_json, size_t state_len)
{
    if (!s || !device_id || !state_json) return QOOAUTH_ERR_INVALID_ARG;

    char path[640];
    build_path(s, "state", device_id, path, sizeof(path));
    return write_file(path, (const uint8_t*)state_json, state_len);
}

qooauth_error_t qooauth_storage_load_state(
    qooauth_storage_t* s, const char* device_id,
    char* out_buf, size_t buf_size, size_t* out_len)
{
    if (!s || !device_id || !out_buf) return QOOAUTH_ERR_INVALID_ARG;

    char path[640];
    build_path(s, "state", device_id, path, sizeof(path));

    size_t len;
    qooauth_error_t err = read_file(path, (uint8_t*)out_buf, buf_size - 1, &len);
    if (err != QOOAUTH_OK) return err;
    out_buf[len] = '\0';
    if (out_len) *out_len = len;
    return QOOAUTH_OK;
}

qooauth_error_t qooauth_storage_delete_state(qooauth_storage_t* s, const char* device_id) {
    if (!s || !device_id) return QOOAUTH_ERR_INVALID_ARG;

    char path[640];
    build_path(s, "state", device_id, path, sizeof(path));
    if (remove(path) != 0 && errno != ENOENT) return QOOAUTH_ERR_STORAGE_WRITE;
    return QOOAUTH_OK;
}

/* ---- Utility ---- */

int qooauth_storage_has_credentials(qooauth_storage_t* s, const char* device_id) {
    if (!s || !device_id) return 0;

    char path[640];
    build_path(s, "keys", device_id, path, sizeof(path));
    if (access(path, F_OK) != 0) return 0;

    build_path(s, "certs", device_id, path, sizeof(path));
    if (access(path, F_OK) != 0) return 0;

    return 1;
}

qooauth_error_t qooauth_storage_list_devices(
    qooauth_storage_t* s, char*** out_ids, size_t* out_count)
{
    /* Stub implementation — platform-dependent directory enumeration
     * should be provided by the integrating platform. */
    if (!s || !out_ids || !out_count) return QOOAUTH_ERR_INVALID_ARG;
    *out_ids = NULL;
    *out_count = 0;
    return QOOAUTH_OK;
}

void qooauth_storage_free_device_list(char** ids, size_t count) {
    if (ids) {
        for (size_t i = 0; i < count; i++) free(ids[i]);
        free(ids);
    }
}
