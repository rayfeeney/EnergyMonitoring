CREATE TABLE EnergyMonitoring.MonitoringDevice
(
    MonitoringDeviceId INT NOT NULL AUTO_INCREMENT
        COMMENT 'Internal identifier for a monitoring device',

    SourceSystemCode VARCHAR(30) NOT NULL
        COMMENT 'Source system providing the device or sensor, e.g. Govee or Tapo',

    SourceDeviceId INT NOT NULL
        COMMENT 'Device identifier within the source system',

    DeviceName VARCHAR(100) NOT NULL
        COMMENT 'Human-readable device or sensor name',

    IsActive TINYINT(1) NOT NULL DEFAULT 1
        COMMENT '1 = active device, 0 = retired',

    CreatedDateTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'Record creation timestamp',

    UpdatedDateTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
        COMMENT 'Last update timestamp',

    PRIMARY KEY (MonitoringDeviceId),

    UNIQUE KEY uxMonitoringDeviceSource
        (SourceSystemCode, SourceDeviceId),

    KEY ixMonitoringDeviceName
        (DeviceName),

    KEY ixMonitoringDeviceActive
        (IsActive),

    CONSTRAINT chkMonitoringDeviceIsActive
        CHECK (IsActive IN (0,1))
)
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
COMMENT='Master list of monitoring devices and sensors from different source systems.';