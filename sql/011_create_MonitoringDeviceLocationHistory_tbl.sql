CREATE TABLE EnergyMonitoring.MonitoringDeviceLocationHistory
(
    MonitoringDeviceLocationHistoryId INT NOT NULL AUTO_INCREMENT
        COMMENT 'Internal identifier for monitoring device location history row',

    MonitoringDeviceId INT NOT NULL
        COMMENT 'Monitoring device being located',

    LocationId INT NOT NULL
        COMMENT 'Physical location of the monitoring device',

    StartDateTime DATETIME NOT NULL
        COMMENT 'Date and time device entered this location',

    EndDateTime DATETIME DEFAULT NULL
        COMMENT 'Date and time device left this location (NULL = current)',

    IsActive TINYINT(1) NOT NULL DEFAULT 1
        COMMENT '1 = valid location assignment, 0 = superseded or erroneous',

    CreatedDateTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        COMMENT 'Record creation timestamp',

    UpdatedDateTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
        COMMENT 'Last update timestamp',

    PRIMARY KEY (MonitoringDeviceLocationHistoryId),

    KEY ixMonitoringDeviceLocationHistoryDeviceTime
        (MonitoringDeviceId, StartDateTime, EndDateTime),

    KEY ixMonitoringDeviceLocationHistoryLocationTime
        (LocationId, StartDateTime, EndDateTime),

    CONSTRAINT fkMonitoringDeviceLocationHistoryDevice
        FOREIGN KEY (MonitoringDeviceId)
        REFERENCES EnergyMonitoring.MonitoringDevice (MonitoringDeviceId),

    CONSTRAINT fkMonitoringDeviceLocationHistoryLocation
        FOREIGN KEY (LocationId)
        REFERENCES orchids.location (locationId),

    CONSTRAINT chkMonitoringDeviceLocationHistoryIsActive
        CHECK (IsActive IN (0,1)),

    CONSTRAINT chkMonitoringDeviceLocationHistoryDateOrder
        CHECK (EndDateTime IS NULL OR EndDateTime > StartDateTime)
)
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
COMMENT='Time-based history of where monitoring devices and sensors have been located.';