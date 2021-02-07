CREATE VIEW view_tipps AS
SELECT f.id AS fixture_id, g.id AS game_id, pg.player_id AS player_id, f.match_start, f."status", f.status_short, f.home_goals, f.away_goals, f.home_odds, f.draw_odds, f.away_odds,
 ht.name AS ht_name, ht.logo AS ht_logo, awt.name AS at_name, awt.logo AS at_logo, l.name AS l_name, l.logo AS l_logo, g.name AS g_name, t.id AS tipp_id, t.tipp_home, t.tipp_away
FROM game_fixture AS f
JOIN game_team AS ht ON ht.id = f.home_team_id
JOIN game_team AS awt ON awt.id = f.away_team_id
JOIN game_league AS l ON l.id = f.league_id
JOIN game_game_leagues AS gl ON gl.league_id = l.id 
JOIN game_player_games AS pg ON pg.game_id = gl.game_id
JOIN game_game AS g ON g.id = gl.game_id
LEFT JOIN game_tipp AS t ON t.fixture_id = f.id AND t.game_id = g.id AND t.player_id = pg.player_id
