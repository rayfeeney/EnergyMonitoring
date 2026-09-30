USE EnergyMonitoring;

CREATE TABLE WeatherHourly
(
    IntervalStartUtc     DATETIME      NOT NULL,

    TemperatureC         DECIMAL(5,2)  NULL,
    RelativeHumidityPct  DECIMAL(5,2)  NULL,

    PrecipitationMm      DECIMAL(7,2)  NULL,
    CloudCoverPct        DECIMAL(5,2)  NULL,

    WindSpeedKmh         DECIMAL(6,2)  NULL,
    WindGustKmh          DECIMAL(6,2)  NULL,

    ShortwaveRadiationWm2 DECIMAL(8,2) NULL,
    DirectRadiationWm2    DECIMAL(8,2) NULL,

    WeatherDataType     VARCHAR(20) NOT NULL,

    LoadedAtUtc          DATETIME      NOT NULL
        DEFAULT UTC_TIMESTAMP(),

    PRIMARY KEY (IntervalStartUtc)
);