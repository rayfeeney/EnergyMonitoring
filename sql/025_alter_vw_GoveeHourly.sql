CREATE OR REPLACE
ALGORITHM = UNDEFINED
VIEW EnergyMonitoring.vw_GoveeHourly
AS

SELECT
    g.EnvironmentSensorId,
    g.MonitoringDeviceId,
    g.SensorName,
    g.IntervalStartUtc,

    CONVERT_TZ(
        g.IntervalStartUtc,
        'UTC',
        'Europe/London'
    ) AS IntervalStart,

    mdlh.LocationId,
    l.locationName AS LocationName,

    g.TemperatureC,
    g.RelativeHumidityPct,
    g.ReadingCount

FROM
(
    SELECT
        es.environmentSensorId AS EnvironmentSensorId,
        md.MonitoringDeviceId AS MonitoringDeviceId,
        er.sensorName AS SensorName,

        TIMESTAMP(
            CAST(
                CONVERT_TZ(
                    er.readingDateTime,
                    'Europe/London',
                    'UTC'
                ) AS DATE
            ),
            MAKETIME(
                HOUR(
                    CONVERT_TZ(
                        er.readingDateTime,
                        'Europe/London',
                        'UTC'
                    )
                ),
                0,
                0
            )
        ) AS IntervalStartUtc,

        CAST(
            AVG(er.temperatureCelsius)
            AS DECIMAL(5,2)
        ) AS TemperatureC,

        CAST(
            AVG(er.relativeHumidity)
            AS DECIMAL(5,2)
        ) AS RelativeHumidityPct,

        COUNT(*) AS ReadingCount

    FROM orchids.environmentreading er

    JOIN orchids.environmentsensor es
        ON es.sensorName = er.sensorName
       AND es.isActive = 1
       AND CAST(er.readingDateTime AS DATE) >= es.effectiveFromDate
       AND (
            es.effectiveToDate IS NULL
            OR CAST(er.readingDateTime AS DATE) < es.effectiveToDate
       )

    JOIN EnergyMonitoring.MonitoringDevice md
        ON md.SourceSystemCode = 'Govee'
       AND md.SourceDeviceId = es.environmentSensorId
       AND md.IsActive = 1

    WHERE
        HOUR(er.readingDateTime) NOT BETWEEN 0 AND 2

        OR TIMEDIFF(
            CONVERT_TZ(
                CONCAT(
                    CAST(er.readingDateTime AS DATE),
                    ' 00:00:00'
                ),
                'Europe/London',
                'UTC'
            ),
            CONCAT(
                CAST(er.readingDateTime AS DATE),
                ' 00:00:00'
            )
        )
        =
        TIMEDIFF(
            CONVERT_TZ(
                CONCAT(
                    CAST(er.readingDateTime AS DATE),
                    ' 03:00:00'
                ),
                'Europe/London',
                'UTC'
            ),
            CONCAT(
                CAST(er.readingDateTime AS DATE),
                ' 03:00:00'
            )
        )

    GROUP BY
        es.environmentSensorId,
        md.MonitoringDeviceId,
        er.sensorName,

        TIMESTAMP(
            CAST(
                CONVERT_TZ(
                    er.readingDateTime,
                    'Europe/London',
                    'UTC'
                ) AS DATE
            ),
            MAKETIME(
                HOUR(
                    CONVERT_TZ(
                        er.readingDateTime,
                        'Europe/London',
                        'UTC'
                    )
                ),
                0,
                0
            )
        )
) g

LEFT JOIN EnergyMonitoring.MonitoringDeviceLocationHistory mdlh
    ON mdlh.MonitoringDeviceId = g.MonitoringDeviceId
   AND mdlh.IsActive = 1
   AND CONVERT_TZ(
        g.IntervalStartUtc,
        'UTC',
        'Europe/London'
   ) >= mdlh.StartDateTime
   AND (
        mdlh.EndDateTime IS NULL
        OR CONVERT_TZ(
            g.IntervalStartUtc,
            'UTC',
            'Europe/London'
        ) < mdlh.EndDateTime
   )

LEFT JOIN orchids.location l
    ON l.locationId = mdlh.LocationId
   AND l.isActive = 1;