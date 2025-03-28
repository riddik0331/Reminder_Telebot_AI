# SQL запрос для получения событий с начала года до сегодняшнего дня
query5 = """
SELECT * FROM date WHERE CAST(STRFTIME('%m%d', event_date) AS INTEGER) < CAST(STRFTIME('%m%d', DATE('now')) AS INTEGER);
"""


# Запрос с подсчетом годовщин событий на сегодняшнюю дату
query1 = """
SELECT event_id AS Номер,
    STRFTIME('%d-%m-%Y', event_date) AS Дата,
    event_name AS Событие,
    CAST(CAST(STRFTIME('%Y', DATE('now')) AS INTEGER) - CAST(STRFTIME('%Y', event_date) AS INTEGER) AS TEXT) || '-я годовщина' AS Разница
FROM date
WHERE CAST(STRFTIME('%m%d', event_date) AS INTEGER) = CAST(STRFTIME('%m%d', DATE('now', '+2 hour')) AS INTEGER);
"""


# SQL запрос на события в текущем месяце
query3 = """
SELECT event_id AS Номер,
    STRFTIME('%d-%m-%Y', event_date) AS Дата,
    event_name AS Событие,
    CAST(CAST(STRFTIME('%Y', DATE('now')) AS INTEGER) - CAST(STRFTIME('%Y', event_date) AS INTEGER) AS TEXT) || '-я годовщина' AS Разница
FROM date
WHERE CAST(STRFTIME('%m', event_date) AS INTEGER) = CAST(STRFTIME('%m', DATE('now')) AS INTEGER);
"""


# Запрос с подсчетом годовщин событий на завтра
query2 = """
SELECT event_id AS Номер,
    STRFTIME('%d-%m-%Y', event_date) AS Дата,
    event_name AS Событие,
    CAST(CAST(STRFTIME('%Y', DATE('now')) AS INTEGER) - CAST(STRFTIME('%Y', event_date) AS INTEGER) AS TEXT) || '-я годовщина' AS Разница
FROM date
WHERE STRFTIME('%m%d', event_date) = STRFTIME('%m%d', DATE('now', '+26 hour'));
"""


# Запрос с подсчетом годовщин событий на следующий месяц
query4 = """
SELECT event_id AS Номер,
    STRFTIME('%d-%m-%Y', event_date) AS Дата,
    event_name AS Событие,
    CAST(CAST(STRFTIME('%Y', DATE('now')) AS INTEGER) - CAST(STRFTIME('%Y', event_date) AS INTEGER) AS TEXT) || '-я годовщина' AS Разница
FROM date
WHERE STRFTIME('%m', event_date) = STRFTIME('%m', DATE('now', '+1 month'));
"""