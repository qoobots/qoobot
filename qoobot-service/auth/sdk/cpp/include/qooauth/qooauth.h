/*
 * qooauth.h — QooBot Device Authentication SDK
 *
 * Copyright (c) 2026 QooBot Authors
 * Licensed under Apache License 2.0
 *
 * Main public header. Include this to use the full SDK.
 *
 * SDK version: 1.0.0
 * Platform: onboard_core (C++17 compatible, pure C API)
 * Dependencies: mbedTLS 3.x, libcurl 8.x (optional), json-c
 *
 * Quick start:
 *
 *   #include <qooauth/qooauth.h>
 *
 *   qooauth_device_config_t cfg = {
 *       .auth_server_url = "https://id.qoobot.com",
 *       .device_serial   = "QBT-2026-0001-ABCD",
 *       .hardware_model  = "QooBot-One-v2",
 *       .storage_root    = "/data/qooauth",
 *   };
 *
 *   qooauth_device_t* dev;
 *   qooauth_device_init(&cfg, &dev);
 *
 *   if (!qooauth_device_is_activated(dev)) {
 *       qooauth_device_activate(dev, NULL);
 *   }
 *
 *   qooauth_device_connect(dev);
 *
 *   char token[2048];
 *   qooauth_device_get_token(dev, token, sizeof(token), NULL);
 *
 *   // ... use token for API calls ...
 *
 *   qooauth_device_destroy(dev);
 */
#ifndef QOOAUTH_H
#define QOOAUTH_H

#include "qooauth_error.h"
#include "qooauth_secure_storage.h"
#include "qooauth_tls.h"
#include "qooauth_cert_manager.h"
#include "qooauth_activation_client.h"
#include "qooauth_device_auth.h"

/** SDK version string. */
#define QOOAUTH_SDK_VERSION      "1.0.0"
#define QOOAUTH_SDK_VERSION_MAJOR 1
#define QOOAUTH_SDK_VERSION_MINOR 0
#define QOOAUTH_SDK_VERSION_PATCH 0

#endif /* QOOAUTH_H */
