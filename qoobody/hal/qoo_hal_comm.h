/**
 * @file qoo_hal_comm.h
 * @brief 通信抽象接口 — CAN FD / EtherCAT / 无线通信
 */

#ifndef QOO_HAL_COMM_H
#define QOO_HAL_COMM_H

#include "qoo_hal_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/*===========================================================================
 * CAN FD 总线
 *===========================================================================*/

/** CAN FD 帧 */
typedef struct {
    uint32_t id;                /**< CAN ID (11/29bit) */
    bool is_extended;           /**< 扩展帧 */
    bool is_fd;                 /**< CAN FD 帧 */
    bool is_remote;             /**< 远程帧 */
    uint8_t dlc;                /**< 数据长度 (0~64) */
    uint8_t data[64];
} qoo_can_frame_t;

/**
 * @brief 发送 CAN 帧
 * @param bus_id CAN 总线 ID
 * @param frame 帧
 */
qoo_error_t qoo_hal_can_send(uint32_t bus_id, const qoo_can_frame_t *frame);

/**
 * @brief 接收 CAN 帧 (非阻塞)
 * @param bus_id CAN 总线 ID
 * @param frame [out] 帧
 * @param timeout_us 超时 (μs)
 */
qoo_error_t qoo_hal_can_recv(uint32_t bus_id, qoo_can_frame_t *frame, uint32_t timeout_us);

/**
 * @brief 注册 CAN 接收回调
 */
qoo_error_t qoo_hal_can_register_callback(uint32_t bus_id,
    void (*callback)(const qoo_can_frame_t *frame, void *user_data),
    void *user_data);

/*===========================================================================
 * EtherCAT
 *===========================================================================*/

/** EtherCAT 从站状态 */
typedef enum {
    ECAT_STATE_INIT = 1,
    ECAT_STATE_PREOP = 2,
    ECAT_STATE_SAFEOP = 4,
    ECAT_STATE_OP = 8,
} qoo_ecat_state_t;

/** EtherCAT 从站信息 */
typedef struct {
    uint16_t alias;
    uint16_t position;
    uint32_t vendor_id;
    uint32_t product_code;
    uint32_t revision;
    qoo_ecat_state_t state;
    uint8_t *pdo_tx;            /**< TxPDO 数据 */
    uint8_t *pdo_rx;            /**< RxPDO 数据 */
    uint16_t pdo_tx_size;
    uint16_t pdo_rx_size;
} qoo_ecat_slave_t;

/**
 * @brief 初始化 EtherCAT 主站
 */
qoo_error_t qoo_hal_ecat_master_init(void);

/**
 * @brief 扫描 EtherCAT 总线从站
 * @param slave_count [out] 发现的从站数量
 */
qoo_error_t qoo_hal_ecat_scan(uint32_t *slave_count);

/**
 * @brief 获取从站信息
 */
qoo_error_t qoo_hal_ecat_get_slave(uint32_t index, qoo_ecat_slave_t *slave);

/**
 * @brief 设置从站状态
 */
qoo_error_t qoo_hal_ecat_set_slave_state(uint32_t index, qoo_ecat_state_t state);

/**
 * @brief 执行一个 EtherCAT 周期 (过程数据交换)
 */
qoo_error_t qoo_hal_ecat_cycle(void);

/*===========================================================================
 * 无线通信
 *===========================================================================*/

/** Wi-Fi 状态 */
typedef struct {
    bool connected;
    int8_t rssi;                /**< 信号强度 (dBm) */
    char ssid[33];
    char ip_addr[16];
    uint32_t tx_rate;           /**< 发送速率 (Mbps) */
    uint32_t rx_rate;           /**< 接收速率 (Mbps) */
} qoo_wifi_status_t;

/** BLE 状态 */
typedef struct {
    bool advertising;           /**< 是否正在广播 */
    bool connected;
    int8_t rssi;
    uint8_t connected_devices;  /**< 已连接设备数 */
} qoo_ble_status_t;

/** UWB 测距 */
typedef struct {
    qoo_timestamp_us_t timestamp;
    uint16_t anchor_id;         /**< 锚点 ID */
    float distance;             /**< 距离 (m) */
    float distance_std;         /**< 距离标准差 (m) */
    int8_t rssi;
} qoo_uwb_range_t;

/**
 * @brief 获取 Wi-Fi 状态
 */
qoo_error_t qoo_hal_wifi_get_status(qoo_wifi_status_t *status);

/**
 * @brief 获取 BLE 状态
 */
qoo_error_t qoo_hal_ble_get_status(qoo_ble_status_t *status);

/**
 * @brief 获取 UWB 测距数据
 * @param ranges [out] 测距数组
 * @param max_count 最大数量
 * @param count [out] 实际数量
 */
qoo_error_t qoo_hal_uwb_get_ranges(qoo_uwb_range_t *ranges,
    uint32_t max_count, uint32_t *count);

#ifdef __cplusplus
}
#endif

#endif /* QOO_HAL_COMM_H */
