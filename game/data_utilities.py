import sqlite3
import pandas as pd
from game.secret import db_name 
from game.models import Tipp, Fixture
from datetime import datetime, date


def GetTippList(game_id, player_id, **kwargs):
    # Helper function to get a list of all relevant games - I could not get this done via the Django ORM - can be replaced with the TippQuery function
    # **filterkw can be used to pass some optional filter values
    # ms_from: date
    # ms_to: date
    # match_status: list of status elements
    # match_status_short: list of status_short elements

    conn = sqlite3.connect(db_name)
    sql = 'SELECT * FROM view_tipps WHERE game_id = ? AND player_id = ? '

    df_tipplist = pd.read_sql(sql,params=[game_id, player_id], con=conn)

    df_tipplist['match_start'] = pd.to_datetime(df_tipplist.match_start)
    df_tipplist['match_day'] = df_tipplist['match_start'].dt.date

    if 'ms_from' in kwargs:
        df_tipplist = df_tipplist[df_tipplist.match_day >= kwargs['ms_from']]

    if 'ms_to' in kwargs:
        df_tipplist = df_tipplist[df_tipplist.match_day <= kwargs['ms_to']]

    cur = conn.cursor()
    sql = sql + ' AND match_start >= ? AND match_start <= ? ORDER BY match_start'
    cur.execute(sql, (game_id, player_id, kwargs['ms_from'].strftime('%Y-%m-%d'),kwargs['ms_to'].strftime('%Y-%m-%d') ))
    
    qs = cur.fetchall()

    return qs
    # return df_tipplist.sort_values(by=['match_start'])  # using a dataframe in the template did not work.


def UpdateGameScores():
    # This function is used to update the scores of each player and is called after each refresh of the API data
    # The score for matches which have finished are marked as final, scores for ongoing matches could still change
    # A fixture is considered finished if it has a status_short of 'FT','AET','PEN', 'ABD' or 'AWD'
    # Only fixtures which have a "not null" value for home_goals are considered (whenever a match has started, the goals become not null)
    # A Draw will always get scores for the correct goal difference (0 in that case)

    # Get all scores which are not set to final (this includes NULL scores as well)
    scores = Tipp.objects.all().filter(yn_final=False, fixture__home_goals__isnull=False)

    # List of status codes for a score to be final
    li_status = ['FT','AET','PEN', 'ABD', 'AWD']

    for score in scores:

        # Determine winner or draw of fixture
        if score.fixture.home_goals > score.fixture.away_goals:
            f_winner = 'H'
        elif score.fixture.home_goals < score.fixture.away_goals:
            f_winner = 'A'
        else:
            f_winner = 'D'

        # same for the tipp
        if score.tipp_home > score.tipp_away:
            t_winner = 'H'
        elif score.tipp_home < score.tipp_away:
            t_winner = 'A'
        else:
            t_winner = 'D'

        if (score.tipp_home == score.fixture.home_goals) and (score.tipp_away == score.fixture.away_goals):
            # Points exact match
            Tipp.objects.filter(id=score.id).update(score = score.game.pts_exact)
        elif (score.tipp_home - score.tipp_away) == (score.fixture.home_goals - score.fixture.away_goals):
            # Points for goal difference
            Tipp.objects.filter(id=score.id).update(score = score.game.pts_difference)
        elif f_winner == t_winner:
            # Points for winner, a draw will never end here, because it would have the correct goal difference (0)
            Tipp.objects.filter(id=score.id).update(score = score.game.pts_winner)
        else:
            # Points for wrong tipp
            Tipp.objects.filter(id=score.id).update(score=score.game.pts_wrong)

        # Set score to final only if match is finished (False is the default value for yn_score )
        if score.fixture.status_short in li_status:
            Tipp.objects.filter(id=score.id).update(yn_final=True)
      
    return scores.count()



def TippQuery(**kwargs):
    # This query is used to return details of fixtures and (if available) tipps for specific games and players
    # As this involves going through a multitude of relations in the database, it was implemented using a the "raw" method
    # Optional Parameters are:
    # integers: player_id, 
    # date objects: from_date, to_date
    # returns a RawQuerySet which can be used in templates to render a page

    sql = '''SELECT f.id AS id, g.id AS game_id, pg.player_id AS player_id, f.match_start, f.status, f.status_short, f.home_goals, f.away_goals, f.home_odds, f.draw_odds, f.away_odds,
        ht.name AS ht_name, ht.logo AS ht_logo, awt.name AS at_name, awt.logo AS at_logo, l.name AS l_name, l.logo AS l_logo, g.name AS g_name, t.id AS tipp_id, t.tipp_home, t.tipp_away
        FROM game_fixture AS f
        JOIN game_team AS ht ON ht.id = f.home_team_id
        JOIN game_team AS awt ON awt.id = f.away_team_id
        JOIN game_league AS l ON l.id = f.league_id
        JOIN game_game_leagues AS gl ON gl.league_id = l.id 
        JOIN game_player_games AS pg ON pg.game_id = gl.game_id
        JOIN game_game AS g ON g.id = gl.game_id
        LEFT JOIN game_tipp AS t ON t.fixture_id = f.id AND t.game_id = g.id AND t.player_id = pg.player_id
        WHERE pg.status_id <= 2 ''' # only if the player is active (status = 2) or the creator (status=1) of the game 

    sql_where = ''
    list_where = list()
    if 'player_id' in kwargs:
        sql_where = sql_where + ' AND pg.player_id = %s '
        list_where.append(kwargs['player_id'])
    
    if 'game_id' in kwargs:
        sql_where = sql_where + ' AND pg.game_id = %s '
        list_where.append(kwargs['game_id'])

    if 'from_date' in kwargs:
        sql_where = sql_where + ' AND f.match_start >= %s '
        list_where.append(kwargs['from_date'].strftime('%Y-%m-%d %H:%M:%S'))
    
    if 'to_date' in kwargs:
        sql_where = sql_where + ' AND f.match_start <= %s '
        list_where.append(kwargs['to_date'].strftime('%Y-%m-%d %H:%M:%S'))

    sql = sql + sql_where + ' ORDER BY f.match_start ASC'

    fixtures = Fixture.objects.raw(sql, list_where)

    return fixtures

