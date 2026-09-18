-- ============================================================
-- STUDENT PRACTICE
-- IPL CRICKET ANALYTICS
-- ============================================================


-- ============================================================
-- QUESTION 1
-- Find the top 10 grounds by number of matches.
-- ============================================================

SELECT
    venue,
    COUNT(DISTINCT match_id) AS matches
FROM matches
GROUP BY venue
ORDER BY matches DESC
LIMIT 10;

-- Explanation:
-- GROUP BY venue groups matches according to the ground.
-- COUNT(DISTINCT match_id) counts each match only once.
-- ORDER BY matches DESC sorts the grounds from highest to lowest.
-- LIMIT 10 returns the top 10 grounds.


-- ============================================================
-- QUESTION 2
-- Find grounds with an average innings score above 165,
-- using a minimum of 25 matches.
-- ============================================================

SELECT
    m.venue,
    ROUND(AVG(i.runs), 2) AS average_innings_score,
    COUNT(DISTINCT i.match_id) AS matches
FROM v_innings i
JOIN matches m
    ON i.match_id = m.match_id
GROUP BY m.venue
HAVING COUNT(DISTINCT i.match_id) >= 25
   AND AVG(i.runs) > 165
ORDER BY average_innings_score DESC;

-- Explanation:
-- v_innings contains the total runs for each innings.
-- AVG(i.runs) calculates the average innings score.
-- JOIN connects innings data with the venue.
-- HAVING filters the grouped results.
-- COUNT(DISTINCT i.match_id) >= 25 ensures at least 25 matches.
-- AVG(i.runs) > 165 selects grounds with an average above 165.


-- ============================================================
-- QUESTION 3
-- Calculate the chase win percentage for grounds
-- with at least 50 matches.
-- ============================================================

SELECT
    venue,
    COUNT(DISTINCT match_id) AS matches,
    SUM(chase_won) AS chases_won,
    ROUND(
        100.0 * SUM(chase_won) / COUNT(DISTINCT match_id),
        2
    ) AS chase_win_percentage
FROM v_match_totals
GROUP BY venue
HAVING COUNT(DISTINCT match_id) >= 50
ORDER BY chase_win_percentage DESC;

-- Explanation:
-- v_match_totals already contains the chase_won column.
-- chase_won = 1 means the chasing team won.
-- chase_won = 0 means the chasing team did not win.
-- SUM(chase_won) counts the number of chase wins.
-- COUNT(DISTINCT match_id) counts the total matches.
-- Chase win percentage = chase wins / total matches * 100.
-- HAVING keeps only grounds with at least 50 matches.


-- ============================================================
-- QUESTION 4
-- Count the number of unique cleaned venues.
-- ============================================================

SELECT
    COUNT(DISTINCT venue) AS unique_venues
FROM matches
WHERE venue IS NOT NULL;

-- Explanation:
-- DISTINCT removes duplicate venue names.
-- COUNT() counts the unique venue names.
-- IS NOT NULL excludes missing venue values.


-- ============================================================
-- QUESTION 5
-- Find the five grounds with the lowest powerplay run rate.
-- ============================================================

SELECT
    m.venue,
    ROUND(
        6.0 * SUM(b.total_runs) / SUM(b.is_legal),
        2
    ) AS powerplay_run_rate
FROM v_ball b
JOIN matches m
    ON b.match_id = m.match_id
WHERE b.phase = 'Powerplay'
GROUP BY m.venue
ORDER BY powerplay_run_rate ASC
LIMIT 5;

-- Explanation:
-- v_ball contains the phase column.
-- phase = 'Powerplay' selects powerplay deliveries.
-- SUM(total_runs) calculates total powerplay runs.
-- SUM(is_legal) counts legal deliveries only.
-- Run rate = total runs / legal balls * 6.
-- ORDER BY ASC sorts from lowest to highest.
-- LIMIT 5 returns the five lowest powerplay run rates.


-- ============================================================
-- QUESTION 6
-- Explain why COUNT(DISTINCT match_id) can be safer than
-- COUNT(*) after a JOIN.
-- ============================================================

SELECT
    COUNT(*) AS total_joined_rows,
    COUNT(DISTINCT m.match_id) AS actual_matches
FROM matches m
JOIN v_ball b
    ON m.match_id = b.match_id;

-- Explanation:
-- v_ball contains one row for each delivery.
-- Therefore, one match can appear in many rows after the JOIN.
-- COUNT(*) counts every row produced by the JOIN.
-- COUNT(DISTINCT m.match_id) counts each match only once.
-- Therefore, COUNT(DISTINCT match_id) is safer when we want
-- to count the actual number of matches.


-- ============================================================
-- QUESTION 7
-- Explain why the day/night question cannot be answered
-- from match_date alone.
-- ============================================================

SELECT
    match_id,
    match_date,
    venue
FROM matches
LIMIT 10;

-- Explanation:
-- match_date contains only the calendar date.
-- It does not contain the match start time.
-- Therefore, match_date alone cannot tell us whether a match
-- was played during the day or at night.
--
-- A time-related column such as start_time, match_time,
-- or a day_night field would be required to determine this.
--
-- The query above demonstrates that match_date gives the date,
-- but not the time of the match.


-- ============================================================
-- END OF STUDENT PRACTICE
-- ============================================================