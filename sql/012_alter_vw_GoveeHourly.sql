CREATE OR REPLACE VIEW EnergyMonitoring.vw_GoveeHourly
AS
SELECT
    es.environmentSensorId AS EnvironmentSensorId,
    md.MonitoringDeviceId,
    er.sensorName AS SensorName,

    TIMESTAMP(
        DATE(CONVERT_TZ(er.readingDateTime, 'Europe/London', 'UTC')),
        MAKETIME(
            HOUR(CONVERT_TZ(er.readingDateTime, 'Europe/London', 'UTC')),
            0,
            0
        )
    ) AS IntervalStartUtc,

    CAST(AVG(er.temperatureCelsius) AS DECIMAL(5,2)) AS TemperatureC,
    CAST(AVG(er.relativeHumidity) AS DECIMAL(5,2)) AS RelativeHumidityPct,
    COUNT(*) AS ReadingCount

FROM orchids.environmentreading AS er

INNER JOIN orchids.environmentsensor AS es
    ON es.sensorName = er.sensorName
    AND es.isActive = 1
    AND DATE(er.readingDateTime) >= es.effectiveFromDate
    AND (
        es.effectiveToDate IS NULL
        OR DATE(er.readingDateTime) < es.effectiveToDate
    )

INNER JOIN EnergyMonitoring.MonitoringDevice AS md
    ON md.SourceSystemCode = 'Govee'
    AND md.SourceDeviceId = es.environmentSensorId
    AND md.IsActive = 1

WHERE NOT (
    HOUR(er.readingDateTime) BETWEEN 0 AND 2

    AND TIMEDIFF(
        CONVERT_TZ(
            CONCAT(DATE(er.readingDateTime), ' 00:00:00'),
            'Europe/London',
            'UTC'
        ),
        CONCAT(DATE(er.readingDateTime), ' 00:00:00')
    )
    <>
    TIMEDIFF(
        CONVERT_TZ(
            CONCAT(DATE(er.readingDateTime), ' 03:00:00'),
            'Europe/London',
            'UTC'
        ),
        CONCAT(DATE(er.readingDateTime), ' 03:00:00')
    )
)

GROUP BY
    es.environmentSensorId,
    md.MonitoringDeviceId,
    er.sensorName,

    TIMESTAMP(
        DATE(CONVERT_TZ(er.readingDateTime, 'Europe/London', 'UTC')),
        MAKETIME(
            HOUR(CONVERT_TZ(er.readingDateTime, 'Europe/London', 'UTC')),
            0,
            0
        )
    );