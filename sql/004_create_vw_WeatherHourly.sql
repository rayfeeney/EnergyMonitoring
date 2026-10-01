CREATE OR REPLACE VIEW vw_WeatherHourly
AS
SELECT
    IntervalStartUtc,
    TemperatureC,
    RelativeHumidityPct,
    PrecipitationMm,
    CloudCoverPct,
    WindSpeedKmh,
    WindGustKmh,
    ShortwaveRadiationWm2,
    DirectRadiationWm2,
    WeatherDataType
FROM WeatherHourly;