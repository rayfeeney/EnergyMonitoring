CREATE OR REPLACE
ALGORITHM = UNDEFINED
VIEW EnergyMonitoring.vw_WeatherHourly
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