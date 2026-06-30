/*
 * qooauth_cert_manager.c — X.509 设备证书管理实现
 */
#include "qooauth/qooauth_cert_manager.h"
#include "qooauth/qooauth_internal.h"

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>

#include <mbedtls/pk.h>
#include <mbedtls/x509_crt.h>
#include <mbedtls/x509_csr.h>
#include <mbedtls/x509_crl.h>
#include <mbedtls/ctr_drbg.h>
#include <mbedtls/entropy.h>
#include <mbedtls/error.h>
#include <mbedtls/pem.h>
#include <mbedtls/sha256.h>
#include <mbedtls/oid.h>

/* ========================================================================
 * Key generation
 * ======================================================================== */

qooauth_error_t qooauth_cert_generate_key_pair(
    qooauth_key_type_t key_type,
    char* out_key_pem, size_t key_buf_size, size_t* out_key_len,
    char* out_pub_pem, size_t pub_buf_size, size_t* out_pub_len)
{
    if (!out_key_pem || key_buf_size < QOOAUTH_MAX_KEY_PEM)
        return QOOAUTH_ERR_INVALID_ARG;

    mbedtls_pk_context pk;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context drbg;

    mbedtls_pk_init(&pk);
    mbedtls_entropy_init(&entropy);
    mbedtls_ctr_drbg_init(&drbg);

    int ret = mbedtls_ctr_drbg_seed(&drbg, mbedtls_entropy_func,
                                     &entropy, NULL, 0);
    if (ret != 0) {
        mbedtls_pk_free(&pk);
        mbedtls_ctr_drbg_free(&drbg);
        mbedtls_entropy_free(&entropy);
        return QOOAUTH_ERR_CERT_GENERATE_KEY;
    }

    /* Generate EC key pair */
    mbedtls_ecp_group_id grp_id = (key_type == QOOAUTH_KEY_EC_P384)
                                   ? MBEDTLS_ECP_DP_SECP384R1
                                   : MBEDTLS_ECP_DP_SECP256R1;

    ret = mbedtls_pk_setup(&pk, mbedtls_pk_info_from_type(MBEDTLS_PK_ECKEY));
    if (ret != 0) {
        mbedtls_pk_free(&pk);
        mbedtls_ctr_drbg_free(&drbg);
        mbedtls_entropy_free(&entropy);
        return QOOAUTH_ERR_CERT_GENERATE_KEY;
    }

    ret = mbedtls_ecp_gen_key(grp_id, mbedtls_pk_ec(pk),
                               mbedtls_ctr_drbg_random, &drbg);
    if (ret != 0) {
        mbedtls_pk_free(&pk);
        mbedtls_ctr_drbg_free(&drbg);
        mbedtls_entropy_free(&entropy);
        return QOOAUTH_ERR_CERT_GENERATE_KEY;
    }

    /* Write private key PEM */
    ret = mbedtls_pk_write_key_pem(&pk, (uint8_t*)out_key_pem, key_buf_size);
    if (ret != 0) {
        mbedtls_pk_free(&pk);
        mbedtls_ctr_drbg_free(&drbg);
        mbedtls_entropy_free(&entropy);
        return QOOAUTH_ERR_CERT_GENERATE_KEY;
    }
    if (out_key_len) *out_key_len = strlen(out_key_pem);

    /* Write public key PEM if requested */
    if (out_pub_pem && pub_buf_size > 0) {
        ret = mbedtls_pk_write_pubkey_pem(&pk, (uint8_t*)out_pub_pem, pub_buf_size);
        if (ret != 0) {
            mbedtls_pk_free(&pk);
            mbedtls_ctr_drbg_free(&drbg);
            mbedtls_entropy_free(&entropy);
            return QOOAUTH_ERR_CERT_GENERATE_KEY;
        }
        if (out_pub_len) *out_pub_len = strlen(out_pub_pem);
    }

    mbedtls_pk_free(&pk);
    mbedtls_ctr_drbg_free(&drbg);
    mbedtls_entropy_free(&entropy);
    return QOOAUTH_OK;
}

/* ========================================================================
 * CSR generation
 * ======================================================================== */

qooauth_error_t qooauth_cert_generate_csr(
    const char* key_pem, size_t key_len,
    const char* subject_dn,
    char* out_csr_pem, size_t csr_buf_size, size_t* out_csr_len)
{
    if (!key_pem || !subject_dn || !out_csr_pem)
        return QOOAUTH_ERR_INVALID_ARG;

    mbedtls_pk_context pk;
    mbedtls_x509write_csr csr;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context drbg;

    mbedtls_pk_init(&pk);
    mbedtls_x509write_csr_init(&csr);
    mbedtls_entropy_init(&entropy);
    mbedtls_ctr_drbg_init(&drbg);

    int ret = mbedtls_ctr_drbg_seed(&drbg, mbedtls_entropy_func,
                                     &entropy, NULL, 0);
    if (ret != 0) goto error;

    /* Parse private key */
    ret = mbedtls_pk_parse_key(&pk, (const uint8_t*)key_pem, key_len + 1,
                                NULL, 0, mbedtls_ctr_drbg_random, &drbg);
    if (ret != 0) goto error;

    /* Set key */
    mbedtls_x509write_csr_set_key(&csr, &pk);

    /* Set MD algorithm */
    mbedtls_x509write_csr_set_md_alg(&csr, MBEDTLS_MD_SHA256);

    /* Set subject */
    ret = mbedtls_x509write_csr_set_subject_name(&csr, subject_dn);
    if (ret != 0) goto error;

    /* Add extensions */
    ret = mbedtls_x509write_csr_set_key_usage(&csr, MBEDTLS_X509_KU_DIGITAL_SIGNATURE);
    if (ret != 0) goto error;

    /* Write CSR PEM */
    ret = mbedtls_x509write_csr_pem(&csr, (uint8_t*)out_csr_pem, csr_buf_size,
                                     mbedtls_ctr_drbg_random, &drbg);
    if (ret != 0) goto error;

    if (out_csr_len) *out_csr_len = strlen(out_csr_pem);

    mbedtls_pk_free(&pk);
    mbedtls_x509write_csr_free(&csr);
    mbedtls_ctr_drbg_free(&drbg);
    mbedtls_entropy_free(&entropy);
    return QOOAUTH_OK;

error:
    mbedtls_pk_free(&pk);
    mbedtls_x509write_csr_free(&csr);
    mbedtls_ctr_drbg_free(&drbg);
    mbedtls_entropy_free(&entropy);
    return QOOAUTH_ERR_CERT_GENERATE_CSR;
}

/* ========================================================================
 * Certificate parsing
 * ======================================================================== */

qooauth_error_t qooauth_cert_parse(
    const uint8_t* cert_pem, size_t cert_len,
    qooauth_cert_info_t* out_info)
{
    if (!cert_pem || !out_info) return QOOAUTH_ERR_INVALID_ARG;

    mbedtls_x509_crt cert;
    mbedtls_x509_crt_init(&cert);

    int ret = mbedtls_x509_crt_parse(&cert, cert_pem, cert_len + 1);
    if (ret != 0) {
        mbedtls_x509_crt_free(&cert);
        return QOOAUTH_ERR_CERT_PARSE;
    }

    memset(out_info, 0, sizeof(*out_info));

    /* Subject DN */
    mbedtls_x509_dn_gets(out_info->subject_dn, sizeof(out_info->subject_dn),
                          &cert.subject);

    /* Issuer DN */
    mbedtls_x509_dn_gets(out_info->issuer_dn, sizeof(out_info->issuer_dn),
                          &cert.issuer);

    /* Serial number */
    size_t o = 0;
    for (size_t i = 0; i < cert.serial.len && o < sizeof(out_info->serial_number) - 2; i++) {
        o += (size_t)snprintf(out_info->serial_number + o,
                               sizeof(out_info->serial_number) - o,
                               "%02X", cert.serial.p[i]);
    }

    /* Fingerprint */
    uint8_t hash[32];
    mbedtls_sha256(cert.raw.p, cert.raw.len, hash, 0);
    qooauth_bin2hex(hash, 32, out_info->fingerprint);

    /* Validity */
    out_info->not_before = (int64_t)mbedtls_x509_time_to_unix(&cert.valid_from);
    out_info->not_after  = (int64_t)mbedtls_x509_time_to_unix(&cert.valid_to);

    /* Key algorithm */
    const char* alg = mbedtls_pk_get_name(&cert.pk);
    qooauth_strncpy_safe(out_info->key_algorithm, alg ? alg : "ECDSA",
                          sizeof(out_info->key_algorithm));

    /* CA flag */
    out_info->is_ca = (cert.ext_types & MBEDTLS_X509_EXT_BASIC_CONSTRAINTS)
                      && cert.ca_istrue;

    mbedtls_x509_crt_free(&cert);
    return QOOAUTH_OK;
}

qooauth_error_t qooauth_cert_verify(
    const uint8_t* cert_pem, size_t cert_len,
    const char* ca_bundle_pem, size_t ca_bundle_len,
    int64_t verify_time)
{
    if (!cert_pem || !ca_bundle_pem) return QOOAUTH_ERR_INVALID_ARG;

    mbedtls_x509_crt cert, ca;
    mbedtls_x509_crt_init(&cert);
    mbedtls_x509_crt_init(&ca);

    int ret = mbedtls_x509_crt_parse(&cert, cert_pem, cert_len + 1);
    if (ret != 0) { mbedtls_x509_crt_free(&cert); mbedtls_x509_crt_free(&ca); return QOOAUTH_ERR_CERT_PARSE; }

    ret = mbedtls_x509_crt_parse(&ca, (const uint8_t*)ca_bundle_pem, ca_bundle_len + 1);
    if (ret != 0) { mbedtls_x509_crt_free(&cert); mbedtls_x509_crt_free(&ca); return QOOAUTH_ERR_CERT_LOAD; }

    uint32_t flags;
    ret = mbedtls_x509_crt_verify(&cert, &ca, NULL, NULL, &flags, NULL, NULL);
    if (ret != 0 || flags != 0) {
        mbedtls_x509_crt_free(&cert);
        mbedtls_x509_crt_free(&ca);
        if (flags & MBEDTLS_X509_BADCERT_EXPIRED) return QOOAUTH_ERR_CERT_EXPIRED;
        if (flags & MBEDTLS_X509_BADCERT_FUTURE) return QOOAUTH_ERR_CERT_NOT_YET_VALID;
        return QOOAUTH_ERR_CERT_VERIFY_CHAIN;
    }

    mbedtls_x509_crt_free(&cert);
    mbedtls_x509_crt_free(&ca);
    return QOOAUTH_OK;
}

qooauth_error_t qooauth_cert_check_key_match(
    const uint8_t* cert_pem, size_t cert_len,
    const char* key_pem, size_t key_len)
{
    if (!cert_pem || !key_pem) return QOOAUTH_ERR_INVALID_ARG;

    mbedtls_x509_crt cert;
    mbedtls_pk_context key;
    mbedtls_x509_crt_init(&cert);
    mbedtls_pk_init(&key);

    int ret = mbedtls_x509_crt_parse(&cert, cert_pem, cert_len + 1);
    if (ret != 0) { mbedtls_x509_crt_free(&cert); mbedtls_pk_free(&key); return QOOAUTH_ERR_CERT_PARSE; }

    ret = mbedtls_pk_parse_key(&key, (const uint8_t*)key_pem, key_len + 1, NULL, 0, NULL, NULL);
    if (ret != 0) { mbedtls_x509_crt_free(&cert); mbedtls_pk_free(&key); return QOOAUTH_ERR_CERT_PARSE; }

    int match = mbedtls_pk_check_pair(&cert.pk, &key, mbedtls_ctr_drbg_random, NULL);

    mbedtls_x509_crt_free(&cert);
    mbedtls_pk_free(&key);

    return match == 0 ? QOOAUTH_OK : QOOAUTH_ERR_CERT_KEY_MISMATCH;
}

/* ========================================================================
 * Expiry monitoring
 * ======================================================================== */

qooauth_error_t qooauth_cert_check_renewal(
    const uint8_t* cert_pem, size_t cert_len,
    int renewal_threshold_days,
    int* out_needs_renewal, int* out_days_remaining)
{
    if (!cert_pem || !out_needs_renewal) return QOOAUTH_ERR_INVALID_ARG;

    qooauth_cert_info_t info;
    qooauth_error_t err = qooauth_cert_parse(cert_pem, cert_len, &info);
    if (err != QOOAUTH_OK) return err;

    int64_t now = (int64_t)time(NULL);
    int64_t remaining = info.not_after - now;
    int days_remaining = (int)(remaining / 86400);

    if (out_days_remaining) *out_days_remaining = days_remaining;

    if (days_remaining < 0) {
        *out_needs_renewal = 1; /* Already expired */
    } else if (days_remaining <= renewal_threshold_days) {
        *out_needs_renewal = 1;
    } else {
        *out_needs_renewal = 0;
    }

    return QOOAUTH_OK;
}

/* ========================================================================
 * CRL (simple in-memory cache)
 * ======================================================================== */

static mbedtls_x509_crl g_crl_cache;
static int g_crl_loaded = 0;

qooauth_error_t qooauth_cert_parse_crl(const uint8_t* crl_der, size_t crl_len) {
    mbedtls_x509_crl_init(&g_crl_cache);
    int ret = mbedtls_x509_crl_parse(&g_crl_cache, crl_der, crl_len);
    if (ret != 0) {
        mbedtls_x509_crl_free(&g_crl_cache);
        return QOOAUTH_ERR_CERT_PARSE;
    }
    g_crl_loaded = 1;
    return QOOAUTH_OK;
}

qooauth_error_t qooauth_cert_check_revoked(const char* serial_hex, int* out_revoked) {
    if (!serial_hex || !out_revoked) return QOOAUTH_ERR_INVALID_ARG;
    if (!g_crl_loaded) { *out_revoked = 0; return QOOAUTH_OK; }

    /* Convert hex serial to binary for comparison */
    const mbedtls_x509_crl* crl = &g_crl_cache;
    while (crl) {
        const mbedtls_x509_crl_entry* entry = &crl->entry;
        while (entry) {
            char buf[128];
            size_t o = 0;
            for (size_t i = 0; i < entry->serial.len && o < sizeof(buf) - 2; i++) {
                o += (size_t)snprintf(buf + o, sizeof(buf) - o, "%02X", entry->serial.p[i]);
            }
            buf[o] = '\0';
            if (strcasecmp(buf, serial_hex) == 0) {
                *out_revoked = 1;
                return QOOAUTH_OK;
            }
            entry = entry->next;
        }
        crl = crl->next;
    }

    *out_revoked = 0;
    return QOOAUTH_OK;
}

void qooauth_cert_clear_crl_cache(void) {
    if (g_crl_loaded) {
        mbedtls_x509_crl_free(&g_crl_cache);
        g_crl_loaded = 0;
    }
}

/* ========================================================================
 * Utility
 * ======================================================================== */

qooauth_error_t qooauth_cert_compute_fingerprint(
    const uint8_t* cert_der, size_t cert_len,
    char* out_hex, size_t out_size)
{
    if (!cert_der || !out_hex || out_size < 65)
        return QOOAUTH_ERR_INVALID_ARG;

    uint8_t hash[32];
    int ret = mbedtls_sha256(cert_der, cert_len, hash, 0);
    if (ret != 0) return QOOAUTH_ERR_CERT_FINGERPRINT;

    qooauth_bin2hex(hash, 32, out_hex);
    return QOOAUTH_OK;
}

qooauth_error_t qooauth_cert_extract_public_key(
    const uint8_t* cert_pem, size_t cert_len,
    char* out_pub_pem, size_t buf_size, size_t* out_len)
{
    if (!cert_pem || !out_pub_pem) return QOOAUTH_ERR_INVALID_ARG;

    mbedtls_x509_crt cert;
    mbedtls_x509_crt_init(&cert);

    int ret = mbedtls_x509_crt_parse(&cert, cert_pem, cert_len + 1);
    if (ret != 0) { mbedtls_x509_crt_free(&cert); return QOOAUTH_ERR_CERT_PARSE; }

    ret = mbedtls_pk_write_pubkey_pem(&cert.pk, (uint8_t*)out_pub_pem, buf_size);
    mbedtls_x509_crt_free(&cert);

    if (ret != 0) return QOOAUTH_ERR_CERT_PARSE;
    if (out_len) *out_len = strlen(out_pub_pem);
    return QOOAUTH_OK;
}
