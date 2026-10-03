CREATE OR REPLACE
ALGORITHM = UNDEFINED
VIEW EnergyMonitoring.vw_EnphaseHourly
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
    h.IntervalCount

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
                ),
                ',',
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
) h;