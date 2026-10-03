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

    teh.EnergyWh

FROM EnergyMonitoring.TapoEnergyHourly teh

JOIN EnergyMonitoring.MonitoringDevice md
    ON md.SourceSystemCode = 'Tapo'
   AND md.SourceDeviceId = teh.TapoDeviceKey
   AND md.IsActive = 1;