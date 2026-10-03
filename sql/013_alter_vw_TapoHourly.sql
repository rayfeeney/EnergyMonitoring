CREATE OR REPLACE VIEW EnergyMonitoring.vw_TapoHourly
AS
SELECT
    teh.TapoDeviceKey,
    md.MonitoringDeviceId,
    teh.HourStartUtc AS IntervalStartUtc,
    teh.EnergyWh
FROM EnergyMonitoring.TapoEnergyHourly AS teh

INNER JOIN EnergyMonitoring.MonitoringDevice AS md
    ON md.SourceSystemCode = 'Tapo'
    AND md.SourceDeviceId = teh.TapoDeviceKey
    AND md.IsActive = 1;