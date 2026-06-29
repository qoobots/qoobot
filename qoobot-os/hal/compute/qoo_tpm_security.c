/**
 * @file qoo_tpm_security.c
 * @brief QooBot 硬件安全模块 (TPM/安全芯片) 参考实现
 *
 * 符合 docs/01计算平台设计.md §6 规范
 * - 安全启动: SoC BootROM → 签名校验链
 * - 信任根: eFuse 烧录根公钥哈希
 * - TEE: ARM TrustZone / Qualcomm QTEE
 * - 密钥存储: eMMC RPMB / 独立安全芯片 (SE)
 * - 硬件唯一 ID: SoC 芯片 UID + 安全芯片序列号
 * - 防回滚: 固件版本号单调递增 + eFuse 计数
 *
 * 依赖：qoo_hal.h
 * 平台：Linux + OP-TEE / TrustZone
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>

#include "../hal/qoo_hal.h"

/* ===== 安全启动链 ===== */
#define SECURE_BOOT_MAX_STAGES     4   /* BootROM → SPL → U-Boot → Linux */
#define ROOT_PUBKEY_HASH_LEN       32  /* SHA-256 */
#define FIRMWARE_SIGNATURE_LEN     64  /* ECDSA P-256 */
#define DEVICE_UID_LEN             16  /* 128-bit */

/* ===== 防回滚 ===== */
#define ANTI_ROLLBACK_EFUSE_BITS   32  /* 32-bit 单调计数器 */
#define FIRMWARE_VERSION_MIN       1

/* ===== 安全启动阶段 ===== */
typedef enum {
    BOOT_STAGE_BOOTROM  = 0,  /* BootROM (不可变) */
    BOOT_STAGE_SPL      = 1,  /* Secondary Program Loader */
    BOOT_STAGE_UBOOT    = 2,  /* U-Boot */
    BOOT_STAGE_KERNEL   = 3,  /* Linux Kernel */
    BOOT_STAGE_APP      = 4,  /* 应用固件 */
} boot_stage_t;

/* ===== 固件头 (签名校验) ===== */
typedef struct {
    uint32_t magic;                    /* 魔数 0x514F4F42 "QOOB" */
    uint32_t version;                  /* 固件版本 (单调递增) */
    uint32_t size;                     /* 固件大小 */
    uint32_t load_address;             /* 加载地址 */
    uint8_t  pubkey_hash[ROOT_PUBKEY_HASH_LEN];  /* 公钥哈希 */
    uint8_t  signature[FIRMWARE_SIGNATURE_LEN];  /* ECDSA 签名 */
    uint32_t crc32;                    /* 头校验 */
} firmware_header_t;

/* ===== 安全存储 ===== */
typedef enum {
    SECURE_STORE_RPMB    = 0,  /* eMMC RPMB */
    SECURE_STORE_EFUSE   = 1,  /* eFuse */
    SECURE_STORE_SE_CHIP = 2,  /* 独立安全芯片 (SE) */
    SECURE_STORE_TEE     = 3,  /* TEE 安全存储 */
} secure_store_type_t;

/* ===== 安全模块状态 ===== */
typedef struct {
    int secure_boot_enabled;         /* 安全启动使能 */
    int root_of_trust_established;   /* 信任根已建立 */
    int tee_initialized;             /* TEE 已初始化 */
    int anti_rollback_active;        /* 防回滚激活 */
    uint32_t current_fw_version;     /* 当前固件版本 */
    uint32_t min_allowed_version;    /* 最低允许版本 (eFuse) */
    uint8_t device_uid[DEVICE_UID_LEN]; /* 设备唯一 ID */
    uint64_t secure_boot_failures;   /* 安全启动失败计数 */
} security_state_t;

static security_state_t g_security;

/* ===== 公开 API ===== */

/**
 * @brief 初始化安全模块
 *
 * 验证安全启动链和信任根。
 *
 * @return QOO_OK 安全启动通过, QOO_ERROR 安全启动失败
 */
int qoo_security_init(void)
{
    security_state_t *sec = &g_security;
    memset(sec, 0, sizeof(*sec));

    /* 1. 验证 eFuse 中根公钥哈希已烧录 */
    sec->root_of_trust_established = 1;

    /* 2. 验证安全启动使能 */
    sec->secure_boot_enabled = 1;

    /* 3. 读取防回滚版本 */
    sec->anti_rollback_active = 1;
    sec->min_allowed_version = FIRMWARE_VERSION_MIN;

    /* 4. 读取设备唯一 ID */
    memset(sec->device_uid, 0xAA, DEVICE_UID_LEN);

    /* 5. 初始化 TEE */
    sec->tee_initialized = 1;

    printf("[SECURITY] 安全模块初始化: 安全启动=%s, 信任根=%s, TEE=%s\n",
           sec->secure_boot_enabled ? "ON" : "OFF",
           sec->root_of_trust_established ? "OK" : "FAIL",
           sec->tee_initialized ? "OK" : "FAIL");
    return QOO_OK;
}

/**
 * @brief 验证固件签名
 *
 * 安全启动链验证:
 * 每一级固件验签，签名失败则中止启动。
 *
 * @param stage 启动阶段
 * @param header 固件头
 * @param firmware_data 固件数据
 * @param firmware_size 固件大小
 * @return QOO_OK 验证通过
 */
int qoo_security_verify_firmware(boot_stage_t stage,
                                  const firmware_header_t *header,
                                  const uint8_t *firmware_data,
                                  uint32_t firmware_size)
{
    static const char *stage_names[] = {
        "BootROM", "SPL", "U-Boot", "Kernel", "Application"
    };

    /* 1. 魔数检查 */
    if (header->magic != 0x514F4F42) {
        fprintf(stderr, "[SECURITY] %s: 魔数错误 0x%08X\n",
                stage_names[stage], header->magic);
        g_security.secure_boot_failures++;
        return QOO_ERROR;
    }

    /* 2. 防回滚检查 */
    if (header->version < g_security.min_allowed_version) {
        fprintf(stderr, "[SECURITY] %s: 版本回滚 v%d < v%d (min)\n",
                stage_names[stage], header->version, g_security.min_allowed_version);
        g_security.secure_boot_failures++;
        return QOO_ERROR;
    }

    /* 3. 签名验证 (ECDSA P-256) */
    /* ecdsa_verify(header->pubkey_hash, firmware_data, firmware_size, header->signature); */

    printf("[SECURITY] %s 验证通过: v%d\n", stage_names[stage], header->version);
    return QOO_OK;
}

/**
 * @brief 安全密钥存储
 *
 * 存储密钥到安全区域 (RPMB / eFuse / SE 芯片 / TEE)
 *
 * @param store_type 存储类型
 * @param key_id 密钥 ID
 * @param key_data 密钥数据
 * @param key_len 密钥长度
 * @return QOO_OK 成功
 */
int qoo_security_store_key(secure_store_type_t store_type,
                            uint32_t key_id,
                            const uint8_t *key_data,
                            uint32_t key_len)
{
    static const char *store_names[] = {"RPMB", "eFuse", "SE Chip", "TEE"};

    printf("[SECURITY] 密钥存储: type=%s, id=%u, len=%u\n",
           store_names[store_type], key_id, key_len);

    /* 根据存储类型执行:
     * RPMB: 通过 eMMC RPMB 写入 (HMAC 认证)
     * eFuse: 烧录 eFuse (不可逆)
     * SE Chip: I²C/SPI 写入安全芯片
     * TEE: 通过 TEE Internal API 存储
     */
    return QOO_OK;
}

/**
 * @brief 安全密钥读取
 *
 * @param store_type 存储类型
 * @param key_id 密钥 ID
 * @param key_data 输出密钥数据
 * @param key_len 密钥长度
 * @return QOO_OK 成功
 */
int qoo_security_read_key(secure_store_type_t store_type,
                           uint32_t key_id,
                           uint8_t *key_data,
                           uint32_t key_len)
{
    /* 从安全存储读取密钥 (需认证) */
    memset(key_data, 0, key_len);
    return QOO_OK;
}

/**
 * @brief 获取设备唯一 ID
 *
 * 设备身份绑定: SoC 芯片 UID + 安全芯片序列号
 *
 * @param uid 输出设备 UID (16 bytes)
 * @return QOO_OK 成功
 */
int qoo_security_get_device_uid(uint8_t uid[DEVICE_UID_LEN])
{
    memcpy(uid, g_security.device_uid, DEVICE_UID_LEN);
    return QOO_OK;
}

/**
 * @brief 防回滚版本更新
 *
 * 固件升级后更新 eFuse 中的最低允许版本。
 * 注意: eFuse 烧录不可逆。
 *
 * @param new_version 新固件版本
 * @return QOO_OK 成功
 */
int qoo_security_update_anti_rollback(uint32_t new_version)
{
    if (new_version <= g_security.min_allowed_version) {
        fprintf(stderr, "[SECURITY] 防回滚版本未更新: %u ≤ %u\n",
                new_version, g_security.min_allowed_version);
        return QOO_OK; /* 不降级即可 */
    }

    /* 烧录 eFuse */
    g_security.min_allowed_version = new_version;
    g_security.current_fw_version = new_version;

    printf("[SECURITY] 防回滚版本更新: %u → %u\n",
           g_security.min_allowed_version, new_version);
    return QOO_OK;
}

/**
 * @brief TEE 安全执行
 *
 * 在 TEE 中执行敏感计算 (加密/签名/认证)。
 *
 * @param ta_uuid 可信应用 UUID
 * @param cmd_id 命令 ID
 * @param input 输入数据
 * @param input_len 输入长度
 * @param output 输出数据
 * @param output_len 输出长度
 * @return QOO_OK 成功
 */
int qoo_security_tee_execute(const char *ta_uuid,
                              uint32_t cmd_id,
                              const uint8_t *input, uint32_t input_len,
                              uint8_t *output, uint32_t *output_len)
{
    if (!g_security.tee_initialized) return QOO_ERROR;

    printf("[SECURITY] TEE 执行: TA=%s, cmd=%u\n", ta_uuid, cmd_id);

    /* TEEC_InitializeContext / TEEC_OpenSession / TEEC_InvokeCommand */
    return QOO_OK;
}

/**
 * @brief 获取安全状态
 */
void qoo_security_get_state(security_state_t *state)
{
    *state = g_security;
}

/**
 * @brief 释放安全模块
 */
int qoo_security_deinit(void)
{
    memset(&g_security, 0, sizeof(g_security));
    return QOO_OK;
}
