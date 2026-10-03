CREATE OR REPLACE
ALGORITHM = UNDEFINED
VIEW EnergyMonitoring.vw_TapoHourly
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

    teh.EnergyWh,

    t.TariffId,
    t.ImportRatePencePerKWh,

    CAST(
        (teh.EnergyWh / 1000.0)
        * t.ImportRatePencePerKWh
        / 100.0
        AS DECIMAL(10,4)
    ) AS EnergyCostGBP

FROM EnergyMonitoring.TapoEnergyHourly teh

JOIN EnergyMonitoring.MonitoringDevice md
    ON md.SourceSystemCode = 'Tapo'
   AND md.SourceDeviceId = teh.TapoDeviceKey
   AND md.IsActive = 1

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