USE EnergyMonitoring;

CREATE TABLE IF NOT EXISTS TapoDevice
(
    TapoDeviceKey INT NOT NULL AUTO_INCREMENT,
    DeviceName VARCHAR(100) NOT NULL,
    Model VARCHAR(20) NOT NULL,
    IpAddress VARCHAR(45) NULL,
    IsActive BOOLEAN NOT NULL DEFAULT TRUE,
    CreatedUtc DATETIME NOT NULL DEFAULT UTC_TIMESTAMP(),

    PRIMARY KEY (TapoDeviceKey)
);

CREATE TABLE IF NOT EXISTS TapoEnergyHourly
(
    TapoDeviceKey INT NOT NULL,
    HourStartUtc DATETIME NOT NULL,
    EnergyWh INT NOT NULL,
    LoadedUtc DATETIME NOT NULL DEFAULT UTC_TIMESTAMP(),

    PRIMARY KEY
    (
        TapoDeviceKey,
        HourStartUtc
    ),

    CONSTRAINT FK_TapoEnergyHourly_TapoDevice
        FOREIGN KEY (TapoDeviceKey)
        REFERENCES TapoDevice(TapoDeviceKey)
);

CREATE TABLE IF NOT EXISTS TapoPowerReading
(
    TapoDeviceKey INT NOT NULL,
    ReadingUtc DATETIME NOT NULL,
    PowerWatts INT NOT NULL,
    LoadedUtc DATETIME NOT NULL DEFAULT UTC_TIMESTAMP(),

    PRIMARY KEY
    (
        TapoDeviceKey,
        ReadingUtc
    ),

    CONSTRAINT FK_TapoPowerReading_TapoDevice
        FOREIGN KEY (TapoDeviceKey)
        REFERENCES TapoDevice(TapoDeviceKey)
);

CREATE TABLE IF NOT EXISTS EnphaseInterval
(
    IntervalEndUtc DATETIME NOT NULL,
    ProducedWh INT NULL,
    ConsumedWh INT NULL,
    ImportedWh INT NULL,
    ExportedWh INT NULL,
    LoadedUtc DATETIME NOT NULL DEFAULT UTC_TIMESTAMP(),

    PRIMARY KEY (IntervalEndUtc)
);

CREATE TABLE IF NOT EXISTS LoadRun
(
    LoadRunKey BIGINT NOT NULL AUTO_INCREMENT,
    SourceName VARCHAR(50) NOT NULL,
    StartedUtc DATETIME NOT NULL,
    CompletedUtc DATETIME NULL,
    RowsReceived INT NULL,
    RowsInserted INT NULL,
    RowsUpdated INT NULL,
    Status VARCHAR(20) NOT NULL,
    ErrorMessage TEXT NULL,

    PRIMARY KEY (LoadRunKey)
);