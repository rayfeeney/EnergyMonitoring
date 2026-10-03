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