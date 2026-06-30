/*
 * qooauth_internal_utils.c — 内部工具函数
 */
#include "qooauth/qooauth_internal.h"
#include <stdio.h>

void qooauth_bin2hex(const uint8_t* in, size_t len, char* out) {
    static const char hex[] = "0123456789abcdef";
    for (size_t i = 0; i < len; i++) {
        out[i * 2]     = hex[(in[i] >> 4) & 0x0F];
        out[i * 2 + 1] = hex[in[i] & 0x0F];
    }
    out[len * 2] = '\0';
}

int qooauth_hex2bin(const char* hex, uint8_t* out, size_t out_size) {
    size_t len = strlen(hex);
    if (len % 2 != 0) return -1;
    len /= 2;
    if (len > out_size) return -1;

    for (size_t i = 0; i < len; i++) {
        char hi = hex[i * 2];
        char lo = hex[i * 2 + 1];
        uint8_t val = 0;

        if (hi >= '0' && hi <= '9') val = (uint8_t)(hi - '0') << 4;
        else if (hi >= 'a' && hi <= 'f') val = (uint8_t)(hi - 'a' + 10) << 4;
        else if (hi >= 'A' && hi <= 'F') val = (uint8_t)(hi - 'A' + 10) << 4;
        else return -1;

        if (lo >= '0' && lo <= '9') val |= (uint8_t)(lo - '0');
        else if (lo >= 'a' && lo <= 'f') val |= (uint8_t)(lo - 'a' + 10);
        else if (lo >= 'A' && lo <= 'F') val |= (uint8_t)(lo - 'A' + 10);
        else return -1;

        out[i] = val;
    }
    return (int)len;
}

static const char base64url_chars[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

int qooauth_base64url_encode(const uint8_t* in, size_t in_len,
                              char* out, size_t out_size) {
    size_t out_len = ((in_len + 2) / 3) * 4;
    if (out_len + 1 > out_size) return -1;

    size_t j = 0;
    for (size_t i = 0; i < in_len; i += 3) {
        uint32_t val = (uint32_t)in[i] << 16;
        if (i + 1 < in_len) val |= (uint32_t)in[i + 1] << 8;
        if (i + 2 < in_len) val |= (uint32_t)in[i + 2];

        out[j++] = base64url_chars[(val >> 18) & 0x3F];
        out[j++] = base64url_chars[(val >> 12) & 0x3F];
        out[j++] = (i + 1 < in_len) ? base64url_chars[(val >> 6) & 0x3F] : '=';
        out[j++] = (i + 2 < in_len) ? base64url_chars[val & 0x3F] : '=';
    }
    out[j] = '\0';
    return (int)j;
}

static int base64url_char_val(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '-') return 62;
    if (c == '_') return 63;
    return -1;
}

int qooauth_base64url_decode(const char* in,
                              uint8_t* out, size_t out_size) {
    size_t in_len = strlen(in);
    if (in_len % 4 != 0) return -1;

    size_t pad = 0;
    if (in_len > 0 && in[in_len - 1] == '=') { pad++; in_len--; }
    if (in_len > 0 && in[in_len - 1] == '=') { pad++; in_len--; }

    size_t out_len = (in_len / 4) * 3 - pad;
    if (out_len > out_size) return -1;

    size_t j = 0;
    for (size_t i = 0; i < in_len; i += 4) {
        int v0 = base64url_char_val(in[i]);
        int v1 = base64url_char_val(in[i + 1]);
        int v2 = (i + 2 < in_len) ? base64url_char_val(in[i + 2]) : 0;
        int v3 = (i + 3 < in_len) ? base64url_char_val(in[i + 3]) : 0;
        if (v0 < 0 || v1 < 0 || v2 < 0 || v3 < 0) return -1;

        uint32_t val = ((uint32_t)v0 << 18) | ((uint32_t)v1 << 12)
                     | ((uint32_t)v2 << 6)  | (uint32_t)v3;
        out[j++] = (uint8_t)(val >> 16);
        if (j < out_len) out[j++] = (uint8_t)(val >> 8);
        if (j < out_len) out[j++] = (uint8_t)val;
    }
    return (int)out_len;
}
