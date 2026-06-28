/*
 * qooauth_error.c — 错误码实现
 */
#include "qooauth/qooauth_error.h"

const char* qooauth_strerror(qooauth_error_t err) {
    switch (err) {
    case QOOAUTH_OK:                        return "Success";

    case QOOAUTH_ERR_INVALID_ARG:           return "Invalid argument";
    case QOOAUTH_ERR_OUT_OF_MEMORY:         return "Out of memory";
    case QOOAUTH_ERR_INTERNAL:              return "Internal error";
    case QOOAUTH_ERR_NOT_INITIALIZED:       return "Not initialized";
    case QOOAUTH_ERR_BUFFER_TOO_SMALL:      return "Buffer too small";
    case QOOAUTH_ERR_NOT_SUPPORTED:         return "Not supported";

    case QOOAUTH_ERR_TLS_INIT:              return "TLS initialization failed";
    case QOOAUTH_ERR_TLS_HANDSHAKE:         return "TLS handshake failed";
    case QOOAUTH_ERR_TLS_CERT_VERIFY:       return "TLS certificate verification failed";
    case QOOAUTH_ERR_TLS_CIPHER_MISMATCH:   return "TLS cipher suite mismatch";
    case QOOAUTH_ERR_TLS_SESSION_EXPIRED:   return "TLS session expired";
    case QOOAUTH_ERR_TLS_WRITE:             return "TLS write failed";
    case QOOAUTH_ERR_TLS_READ:              return "TLS read failed";

    case QOOAUTH_ERR_CERT_LOAD:             return "Certificate load failed";
    case QOOAUTH_ERR_CERT_PARSE:            return "Certificate parse failed";
    case QOOAUTH_ERR_CERT_EXPIRED:          return "Certificate expired";
    case QOOAUTH_ERR_CERT_NOT_YET_VALID:    return "Certificate not yet valid";
    case QOOAUTH_ERR_CERT_REVOKED:          return "Certificate revoked";
    case QOOAUTH_ERR_CERT_VERIFY_CHAIN:     return "Certificate chain verification failed";
    case QOOAUTH_ERR_CERT_KEY_MISMATCH:     return "Certificate/key mismatch";
    case QOOAUTH_ERR_CERT_SAVE:             return "Certificate save failed";
    case QOOAUTH_ERR_CERT_GENERATE_KEY:     return "Key generation failed";
    case QOOAUTH_ERR_CERT_GENERATE_CSR:     return "CSR generation failed";
    case QOOAUTH_ERR_CERT_RENEWAL_NEEDED:   return "Certificate renewal needed";
    case QOOAUTH_ERR_CERT_FINGERPRINT:      return "Fingerprint computation failed";

    case QOOAUTH_ERR_STORAGE_OPEN:          return "Storage open failed";
    case QOOAUTH_ERR_STORAGE_READ:          return "Storage read failed";
    case QOOAUTH_ERR_STORAGE_WRITE:         return "Storage write failed";
    case QOOAUTH_ERR_STORAGE_INTEGRITY:     return "Storage integrity check failed";
    case QOOAUTH_ERR_STORAGE_LOCKED:        return "Storage locked";
    case QOOAUTH_ERR_STORAGE_NOT_FOUND:     return "Storage entry not found";
    case QOOAUTH_ERR_STORAGE_PERMISSION:    return "Storage permission denied";
    case QOOAUTH_ERR_STORAGE_FULL:          return "Storage full";

    case QOOAUTH_ERR_ACTIVATION_HTTP:       return "Activation HTTP request failed";
    case QOOAUTH_ERR_ACTIVATION_JSON:       return "Activation JSON parse failed";
    case QOOAUTH_ERR_ACTIVATION_REJECTED:   return "Activation rejected by server";
    case QOOAUTH_ERR_ACTIVATION_TIMEOUT:    return "Activation timed out";
    case QOOAUTH_ERR_ACTIVATION_CHALLENGE:  return "Activation challenge failed";
    case QOOAUTH_ERR_ACTIVATION_VERIFY:     return "Activation verification failed";
    case QOOAUTH_ERR_ACTIVATION_RETRY:      return "Activation retry limit exceeded";
    case QOOAUTH_ERR_ACTIVATION_MAX_ATTEMPTS:return "Activation max attempts exceeded";

    case QOOAUTH_ERR_NETWORK_CONNECT:       return "Network connect failed";
    case QOOAUTH_ERR_NETWORK_TIMEOUT:       return "Network timeout";
    case QOOAUTH_ERR_NETWORK_DNS:           return "DNS resolution failed";
    case QOOAUTH_ERR_NETWORK_PROTOCOL:      return "Network protocol error";
    case QOOAUTH_ERR_NETWORK_HTTP_STATUS:   return "Unexpected HTTP status";

    case QOOAUTH_ERR_TOKEN_EXPIRED:         return "Token expired";
    case QOOAUTH_ERR_TOKEN_INVALID:         return "Token invalid";
    case QOOAUTH_ERR_TOKEN_REVOKED:         return "Token revoked";

    default:                                return "Unknown error";
    }
}
