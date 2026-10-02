CREATE OR REPLACE VIEW vw_TapoHourly
AS
SELECT
    TapoDeviceKey,
    HourStartUtc AS IntervalStartUtc,
    EnergyWh
FROM TapoEnergyHourly;