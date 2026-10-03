CREATE OR REPLACE VIEW EnergyMonitoring.vw_GoveeHourly
AS
SELECT
    sensorName AS SensorName,

    TIMESTAMP(
        DATE(CONVERT_TZ(readingDateTime, 'Europe/London', 'UTC')),
        MAKETIME(
            HOUR(CONVERT_TZ(readingDateTime, 'Europe/London', 'UTC')),
            0,
            0
        )
    ) AS IntervalStartUtc,

    CAST(
        AVG(temperatureCelsius)
        AS DECIMAL(5,2)
    ) AS TemperatureC,

    CAST(
        AVG(relativeHumidity)
        AS DECIMAL(5,2)
    ) AS RelativeHumidityPct,

    COUNT(*) AS ReadingCount

FROM orchids.environmentreading

WHERE NOT (
    HOUR(readingDateTime) = 1

    AND TIMEDIFF(
        CONVERT_TZ(
            CONCAT(DATE(readingDateTime), ' 00:00:00'),
            'Europe/London',
            'UTC'
        ),
        CONCAT(DATE(readingDateTime), ' 00:00:00')
    )
    <>
    TIMEDIFF(
        CONVERT_TZ(
            CONCAT(DATE(readingDateTime), ' 03:00:00'),
            'Europe/London',
            'UTC'
        ),
        CONCAT(DATE(readingDateTime), ' 03:00:00')
    )
)

GROUP BY
    sensorName,

    TIMESTAMP(
        DATE(CONVERT_TZ(readingDateTime, 'Europe/London', 'UTC')),
        MAKETIME(
            HOUR(CONVERT_TZ(readingDateTime, 'Europe/London', 'UTC')),
            0,
            0
        )
    );