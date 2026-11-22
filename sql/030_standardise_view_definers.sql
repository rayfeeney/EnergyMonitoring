-- Standardise the six EnergyMonitoring view definers.
-- MariaDB 11.8 compatibility and Pi 2 standby restore.
-- Preserves existing view SELECT definitions.

CREATE OR REPLACE
ALGORITHM = UNDEFINED
DEFINER = `root`@`localhost` SQL SECURITY DEFINER VIEW EnergyMonitoring.vw_EnphaseHourly
AS

SELECT
    h.IntervalStartUtc,

    CONVERT_TZ(
        h.IntervalStartUtc,
        'UTC',
        'Europe/London'
    ) AS IntervalStart,

    h.ProducedWh,
    h.ConsumedWh,
    h.ImportedWh,
    h.ExportedWh,
    h.ChargedWh,
    h.DischargedWh,
    h.BatterySocPct,
    h.IntervalCount,

    t.TariffId,
    t.ImportRatePencePerKWh,

    CAST(
        (h.ImportedWh / 1000.0)
        * t.ImportRatePencePerKWh
        / 100.0
        AS DECIMAL(10,4)
    ) AS ImportCostGBP,

    CASE
        WHEN t.ExportEffectiveFromDate IS NOT NULL
         AND DATE(
                CONVERT_TZ(
                    h.IntervalStartUtc,
                    'UTC',
                    'Europe/London'
                )
             ) >= t.ExportEffectiveFromDate
        THEN t.ExportRatePencePerKWh
        ELSE NULL
    END AS ExportRatePencePerKWh,

    CASE
        WHEN t.ExportEffectiveFromDate IS NOT NULL
         AND DATE(
                CONVERT_TZ(
                    h.IntervalStartUtc,
                    'UTC',
                    'Europe/London'
                )
             ) >= t.ExportEffectiveFromDate
         AND t.ExportRatePencePerKWh IS NOT NULL
        THEN CAST(
            (h.ExportedWh / 1000.0)
            * t.ExportRatePencePerKWh
            / 100.0
            AS DECIMAL(10,4)
        )
        ELSE NULL
    END AS ExportIncomeGBP

FROM
(
    SELECT
        CAST(
            DATE_FORMAT(
                IntervalEndUtc - INTERVAL 1 SECOND,
                '%Y-%m-%d %H:00:00'
            ) AS DATETIME
        ) AS IntervalStartUtc,

        SUM(ProducedWh)   AS ProducedWh,
        SUM(ConsumedWh)   AS ConsumedWh,
        SUM(ImportedWh)   AS ImportedWh,
        SUM(ExportedWh)   AS ExportedWh,
        SUM(ChargedWh)    AS ChargedWh,
        SUM(DischargedWh) AS DischargedWh,

        CAST(
            SUBSTRING_INDEX(
                GROUP_CONCAT(
                    BatterySocPct
                    ORDER BY IntervalEndUtc DESC
                    SEPARATOR ','
                ) COLLATE utf8mb4_general_ci,
                ',' COLLATE utf8mb4_general_ci,
                1
            ) AS DECIMAL(5,2)
        ) AS BatterySocPct,

        COUNT(*) AS IntervalCount

    FROM EnergyMonitoring.EnphaseInterval

    GROUP BY
        CAST(
            DATE_FORMAT(
                IntervalEndUtc - INTERVAL 1 SECOND,
                '%Y-%m-%d %H:00:00'
            ) AS DATETIME
        )
) h

LEFT JOIN EnergyMonitoring.Tariff t
    ON DATE(
        CONVERT_TZ(
            h.IntervalStartUtc,
            'UTC',
            'Europe/London'
        )
    )
    BETWEEN t.EffectiveFromDate
        AND COALESCE(t.EffectiveToDate, '9999-12-31');

CREATE OR REPLACE
ALGORITHM = UNDEFINED
DEFINER = `root`@`localhost` SQL SECURITY DEFINER VIEW EnergyMonitoring.vw_GoveeHourly
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
    g.ReadingCount,

    CASE
        WHEN HOUR(g.IntervalStartUtc) >= 6
         AND HOUR(g.IntervalStartUtc) < 18
        THEN 'Day'
        ELSE 'Night'
    END AS TargetPeriod,

    CASE
        WHEN HOUR(g.IntervalStartUtc) >= 6
         AND HOUR(g.IntervalStartUtc) < 18
        THEN etr.expectedDayTemperatureCelsius
        ELSE etr.expectedNightTemperatureCelsius
    END AS ExpectedTemperatureC,

    etr.expectedRelativeHumidity
        AS ExpectedRelativeHumidityPct,

    CAST(
        g.TemperatureC
        -
        CASE
            WHEN HOUR(g.IntervalStartUtc) >= 6
             AND HOUR(g.IntervalStartUtc) < 18
            THEN etr.expectedDayTemperatureCelsius
            ELSE etr.expectedNightTemperatureCelsius
        END
        AS DECIMAL(6,2)
    ) AS TemperatureVarianceC,

    CAST(
        g.RelativeHumidityPct
        - etr.expectedRelativeHumidity
        AS DECIMAL(6,2)
    ) AS RelativeHumidityVariancePct

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
   AND l.isActive = 1

LEFT JOIN EnergyMonitoring.GreenhouseTargetLocationMap gtlm
    ON gtlm.LocationId = mdlh.LocationId

LEFT JOIN orchids.environmenttargetrule etr
    ON etr.locationName = gtlm.TargetRuleLocationName
   AND etr.monthNumber = MONTH(
        CONVERT_TZ(
            g.IntervalStartUtc,
            'UTC',
            'Europe/London'
        )
   )
   AND etr.isActive = 1
   AND DATE(
        CONVERT_TZ(
            g.IntervalStartUtc,
            'UTC',
            'Europe/London'
        )
   ) >= etr.effectiveFromDate
   AND (
        etr.effectiveToDate IS NULL
        OR DATE(
            CONVERT_TZ(
                g.IntervalStartUtc,
                'UTC',
                'Europe/London'
            )
        ) < etr.effectiveToDate
   );

CREATE OR REPLACE DEFINER = `root`@`localhost` SQL SECURITY DEFINER VIEW EnergyMonitoring.vw_MonitoringDeviceLocation
AS
SELECT
    md.MonitoringDeviceId,
    md.SourceSystemCode,
    md.SourceDeviceId,
    md.DeviceName,
    mdlh.LocationId,
    l.locationName AS LocationName,
    mdlh.StartDateTime,
    mdlh.EndDateTime
FROM EnergyMonitoring.MonitoringDevice AS md

INNER JOIN EnergyMonitoring.MonitoringDeviceLocationHistory AS mdlh
    ON mdlh.MonitoringDeviceId = md.MonitoringDeviceId
    AND mdlh.IsActive = 1

INNER JOIN orchids.location AS l
    ON l.locationId = mdlh.LocationId

WHERE md.IsActive = 1
  AND l.isActive = 1;

CREATE OR REPLACE
ALGORITHM = UNDEFINED
DEFINER = `root`@`localhost` SQL SECURITY DEFINER VIEW EnergyMonitoring.vw_TapoHourly
AS

SELECT
    teh.TapoDeviceKey,
    md.MonitoringDeviceId,

    teh.HourStartUtc AS IntervalStartUtc,

    CONVERT_TZ(
        teh.HourStartUtc,
        'UTC',
        'Europe/London'
    ) AS IntervalStart,

    mdlh.LocationId,
    l.locationName AS LocationName,

    teh.EnergyWh,

    t.TariffId,
    t.ImportRatePencePerKWh,

    CAST(
        teh.EnergyWh / 1000.0
        * t.ImportRatePencePerKWh
        / 100.0
        AS DECIMAL(10,4)
    ) AS EnergyCostGBP

FROM EnergyMonitoring.TapoEnergyHourly teh

JOIN EnergyMonitoring.MonitoringDevice md
    ON md.SourceSystemCode = 'Tapo'
   AND md.SourceDeviceId = teh.TapoDeviceKey
   AND md.IsActive = 1

LEFT JOIN EnergyMonitoring.MonitoringDeviceLocationHistory mdlh
    ON mdlh.MonitoringDeviceId = md.MonitoringDeviceId
   AND mdlh.IsActive = 1
   AND CONVERT_TZ(
           teh.HourStartUtc,
           'UTC',
           'Europe/London'
       ) >= mdlh.StartDateTime
   AND (
        mdlh.EndDateTime IS NULL
        OR CONVERT_TZ(
               teh.HourStartUtc,
               'UTC',
               'Europe/London'
           ) < mdlh.EndDateTime
   )

LEFT JOIN orchids.location l
    ON l.locationId = mdlh.LocationId
   AND l.isActive = 1

LEFT JOIN EnergyMonitoring.Tariff t
    ON DATE(
        CONVERT_TZ(
            teh.HourStartUtc,
            'UTC',
            'Europe/London'
        )
    )
    BETWEEN t.EffectiveFromDate
        AND COALESCE(t.EffectiveToDate, '9999-12-31');

CREATE OR REPLACE DEFINER = `root`@`localhost` SQL SECURITY DEFINER VIEW EnergyMonitoring.vw_Tariff
AS
SELECT
    TariffId,
    SupplierName,
    TariffName,
    EffectiveFromDate,
    EffectiveToDate,
    ImportRatePencePerKWh,
    StandingChargePencePerDay,
    ExportRatePencePerKWh,
    ExitFeeGBP,
    ExitFeeAppliesUntilDate
FROM EnergyMonitoring.Tariff;

CREATE OR REPLACE
ALGORITHM = UNDEFINED
DEFINER = `root`@`localhost` SQL SECURITY DEFINER VIEW EnergyMonitoring.vw_WeatherHourly
AS

SELECT
    wh.IntervalStartUtc,

    CONVERT_TZ(
        wh.IntervalStartUtc,
        'UTC',
        'Europe/London'
    ) AS IntervalStart,

    wh.TemperatureC,
    wh.RelativeHumidityPct,
    wh.PrecipitationMm,
    wh.CloudCoverPct,
    wh.WindSpeedKmh,
    wh.WindGustKmh,
    wh.ShortwaveRadiationWm2,
    wh.DirectRadiationWm2,
    wh.WeatherDataType

FROM EnergyMonitoring.WeatherHourly wh;