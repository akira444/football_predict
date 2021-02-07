import requests
import pandas as pd
from datetime import datetime, date, timedelta
from django.utils.timezone import make_aware
import sqlite3
from game.secret import api_headers, db_name, leagues_list
from game.models import UpdateSchedule, Fixture, Team, League
from game.data_utilities import UpdateGameScores

def update_countries():
    # Fill Country table - only run once, or update rarely
    headers = api_headers
    conn = sqlite3.connect(db_name) 

    response = requests.get('https://api-football-v1.p.rapidapi.com/v2/countries', headers=headers)
    countries = response.json()
    countries = countries['api']['countries']

    df_countries = pd.DataFrame(countries)

    cur = conn.cursor()
    for country in df_countries.itertuples(index=False):
        cur.execute('SELECT name FROM game_country WHERE name = ?', (country.country,))
        try:
            id = cur.fetchone()[0]
            # Country exists - update
        except:
            # New counry - insert
            cur.execute('INSERT INTO game_country (name, code, flag) VALUES (?,?,?)', (country.country, country.code, country.flag) )
            conn.commit()
    cur.close()


def update_leagues():
    headers = api_headers
    conn = sqlite3.connect(db_name) 

    # Read countries from database 
    df_db_countries = pd.read_sql('SELECT id AS my_country_id, name as country FROM game_country', con=conn)

    # Update Leagues
    response = requests.get('https://api-football-v1.p.rapidapi.com/v2/leagues/current',headers=headers)
    leagues = response.json()
    leagues = leagues['api']['leagues']

    df_leagues = pd.DataFrame(leagues, columns=['league_id', 'name', 'type', 'country', 'season', 'season_start', 'season_end', 'logo']) #Convert the leagues data to pandas dataframe

    # Filter only relevant leagues
    df_leagues = df_leagues[df_leagues.league_id.isin(leagues_list)]

    # Join Data to get internal country ID
    df_leagues = pd.merge(df_leagues,df_db_countries,on='country')

    # insert leagues in database
    new_leagues = 0
    cur = conn.cursor()
    for league in df_leagues.itertuples(index=False):#itertuples have to be used to loop through dataframe
        cur.execute('SELECT id FROM game_league WHERE api_id = ?', (league.league_id,))
        try:
            id = cur.fetchone()[0]
            # League exists - update
            cur.execute(''' UPDATE game_league SET name = ?, season = ?, season_start = ?, season_end = ?, logo = ?, country_id = ? 
                WHERE api_id = ?''', (league.name, league.season, league.season_start, league.season_end, league.logo, league.my_country_id, id ))
            conn.commit()
        except:
            # League does not exist - insert
            cur.execute('''INSERT INTO game_league (api_id, name, is_current, season, season_start, season_end, logo, country_id )
                VALUES (?,?,?,?,?,?,?,?)''', (league.league_id, league.name, 1, league.season, league.season_start, league.season_end, league.logo, league.my_country_id))
            conn.commit()
            new_leagues += 1
    cur.close() 

    return new_leagues


def update_teams():
    headers = api_headers
    conn = sqlite3.connect(db_name) 

    # Read countries from database 
    df_db_countries = pd.read_sql('SELECT id AS my_country_id, name as country FROM game_country', con=conn)

    # Fill teams table in database for all leagues
    # First initialise the dataframe holding all the data
    df_teams = pd.DataFrame(columns=['team_id','name','logo', 'country'])
    for league in leagues_list:
        teams_url = 'https://api-football-v1.p.rapidapi.com/v2/teams/league/' + str(league)
        response = requests.get(teams_url, headers=headers)
        teams = response.json()
        teams = teams['api']['teams']

        # temporary dataframe to merge with df_teams
        df_temp = pd.DataFrame(teams, columns=['team_id','name','logo','country'])
        df_teams = df_teams.append(df_temp) # append the dataframe

    # Drop duplicate values (teams can play in more than one league / competition)
    df_teams = df_teams.drop_duplicates()

    # Join with countries to get internal country id
    df_teams = pd.merge(df_teams,df_db_countries,on='country')

    # Insert into Database
    cur = conn.cursor()
    for team in df_teams.itertuples(index=False):
        cur.execute('SELECT id FROM game_team WHERE api_id = ?', (team.team_id,))
        try:
            id = cur.fetchone()[0]
            # Team exists - update
            cur.execute('''UPDATE game_team SET name = ?, logo = ?, country_id = ? 
                WHERE id = ?''', (team.name, team.logo, team.my_country_id, id))
            conn.commit()
        except:
            # Team does not exist - insert
            cur.execute('''INSERT INTO game_team (api_id, name, logo, country_id)
                VALUES (?,?,?,?)''', (team.team_id, team.name, team.logo, team.my_country_id))
            conn.commit()
    cur.close() 

def api_fixtures(api_url):
    # API Call and parsing of fixtures data
    headers = api_headers
    querystring = {"timezone":"Europe/Vienna"}

    response = requests.get(api_url, headers=headers,params=querystring)
    fixtures = response.json()
    fixtures = fixtures['api']['fixtures']

    for fixture in fixtures:
        fixture['homeTeam_id'] = fixture['homeTeam']['team_id']
        fixture['homeTeam_name'] = fixture['homeTeam']['team_name']
        fixture['awayTeam_id'] = fixture['awayTeam']['team_id']
        fixture['awayTeam_name'] = fixture['awayTeam']['team_name']

    return fixtures


def get_fixtures(df_fixtures, **updatemode):
    # **updatemode allows to pass flexible parameters as key-value pairs

    if updatemode['mode'] == 'leagues':
        # fixtures for all leagues in leagues list are updated
        for league in updatemode['leagues_list']:
            fixtures_url = 'https://api-football-v1.p.rapidapi.com/v2/fixtures/league/' + str(league)
            fixtures = api_fixtures(fixtures_url)    
            df_temp = pd.DataFrame(fixtures, columns=list(df_fixtures.columns)) 
            df_fixtures = df_fixtures.append(df_temp)

    elif updatemode['mode'] == 'days':
        # fixtures for today + 2 days are updated
        for matchday in updatemode['matchdays']:
            fixtures_url = 'https://api-football-v1.p.rapidapi.com/v2/fixtures/date/' + matchday
            fixtures = api_fixtures(fixtures_url)    
            df_temp = pd.DataFrame(fixtures, columns=list(df_fixtures.columns)) 
            df_fixtures = df_fixtures.append(df_temp)

    else:
        # live games are updated - all from current day
        td = date.today()
        fixtures_url = 'https://api-football-v1.p.rapidapi.com/v2/fixtures/date/' + td.strftime('%Y-%m-%d')
        fixtures = api_fixtures(fixtures_url)
        df_fixtures = pd.DataFrame(fixtures, columns=list(df_fixtures.columns)) 

    return df_fixtures

def is_float(test_string):
    # returns true if a string can be converted to a float, and false otherwise
    try:
        float(test_string)
        return True
    except:
        return False

def get_odds(fixtures):
    # Get odds from API for all fixtures in the dataframe
    # Every odd is per fixture as the api only returns ten results if all odds per day are requested

    headers = api_headers
    querystring = {"timezone":"Europe/Vienna"}

    df_odds = pd.DataFrame(columns=['fixture_id', 'home_win', 'draw', 'away_win'])
    # Odds for a date
    for fixture in fixtures:
        # label = 1 is the Match Winner Bet
        odds_url = 'https://api-football-v1.p.rapidapi.com/v2/odds/fixture/' + str(fixture) + '/label/1'
        response = requests.get(odds_url, headers=headers,params=querystring)
        odds = response.json()
        if 'api' in odds:
            if 'odds' in odds['api']:
                odds = odds['api']['odds']

                for o in odds:
                    o['fixture_id'] = o['fixture']['fixture_id']
                    o['bookmaker_home'] = 0
                    o['home_win'] = 0
                    o['bookmaker_draw'] = 0
                    o['draw'] = 0
                    o['bookmaker_away'] = 0
                    o['away_win'] = 0
                    for bookmaker in o['bookmakers']:
                        for bet in bookmaker['bets']:
                            if bet['label_name'] == 'Match Winner':
                                for bet_value in bet['values']:
                                    if bet_value['value'] == 'Home' and is_float(bet_value['odd']):
                                        o['bookmaker_home'] += 1
                                        o['home_win'] += float(bet_value['odd'])
                                    elif bet_value['value'] == 'Draw' and is_float(bet_value['odd']):
                                        o['bookmaker_draw'] += 1
                                        o['draw'] += float(bet_value['odd'])
                                    elif bet_value['value'] == 'Away' and is_float(bet_value['odd']):
                                        o['bookmaker_away'] += 1
                                        o['away_win'] += float(bet_value['odd'])

                    if o['bookmaker_home'] > 0:
                        o['home_win'] = o['home_win'] / o['bookmaker_home']
                    if o['bookmaker_draw'] > 0:
                        o['draw'] = o['draw'] / o['bookmaker_draw']
                    if o['bookmaker_away'] > 0:
                        o['away_win'] = o['away_win'] / o['bookmaker_away']

                df_temp = pd.DataFrame(odds, columns=['fixture_id', 'home_win', 'draw', 'away_win'])
                df_odds = df_odds.append(df_temp)

    return df_odds
    

def update_fixtures(mode):
    # Load Fixtures for Database - different modes are possible
    # 'leagues' => update all fixtures for all leagues in leagues_list
    # 'days' => update all fixtures for yesterday, today + 2 days into the future
    # 'live' => update all fixtures currently playing

    conn = sqlite3.connect(db_name) 

    df_fixtures = pd.DataFrame(columns=['fixture_id', 'league_id', 'event_date', 'round', 'status', 'statusShort', 'homeTeam_id','awayTeam_id','goalsHomeTeam','goalsAwayTeam'])

    # Depending on mode - get data from API
    if mode == 'leagues':
        df_fixtures = get_fixtures(df_fixtures, mode=mode, leagues_list = leagues_list)
    elif mode == 'days':
        td = date.today() # get current date
        matchdays = [(td+timedelta(days=-1)).strftime('%Y-%m-%d'), td.strftime('%Y-%m-%d'), (td+timedelta(days=1)).strftime('%Y-%m-%d'), (td+timedelta(days=2)).strftime('%Y-%m-%d')]
        df_fixtures = get_fixtures(df_fixtures, mode=mode, matchdays = matchdays)
    else:
        # live games
        df_fixtures = get_fixtures(df_fixtures, mode=mode)

    # Remove duplicates - just in case
    df_fixtures = df_fixtures.drop_duplicates()

    # convert starttime to datetime object to avoid problems in database
    df_fixtures['dt_event_date'] = pd.to_datetime(df_fixtures.event_date)

    # internal ids for teams and league have to be added
    # Read from database into pandas dataframe
    df_db_leagues = pd.read_sql('SELECT id AS my_league_id, api_id AS league_id FROM game_league', con=conn)
    df_db_teams = pd.read_sql('SELECT id AS my_team_id, api_id as team_id FROM game_team', con=conn)

    # Join Data to get my internal IDs
    # first the leagues, as this is an inner join it also get's rid of fixtures which are not in a relevant league
    df_fixtures = pd.merge(df_fixtures,df_db_leagues,on='league_id')

    # Update odds only for relevant fixtures and only in mode 'days'
    if mode == 'days':
        df_fixtures_today = df_fixtures[(df_fixtures.dt_event_date < matchdays[2]) & (df_fixtures.dt_event_date > matchdays[0])]
        df_odds = get_odds(df_fixtures_today['fixture_id'].tolist()) # odds are only updated for current day + two days, but not for live games
        # Join odds data with fixtures data - not all fixtures have odds available - therefore a left outer join has to be used
        df_fixtures = pd.merge(df_fixtures, df_odds, how='left', on='fixture_id')
    else:
        df_fixtures = df_fixtures.reindex(df_fixtures.columns.tolist() + ['home_win','draw','away_win'], axis = 1)  # add the columns which usually come from odds 
 
    # home team
    df_db_hometeams = df_db_teams.rename(columns={'my_team_id' : 'my_homeTeam_id', 'team_id' : 'homeTeam_id'})
    df_fixtures = pd.merge(df_fixtures,df_db_hometeams, on='homeTeam_id')

    # away team
    df_db_awayteams = df_db_teams.rename(columns={'my_team_id' : 'my_awayTeam_id', 'team_id' : 'awayTeam_id'})
    df_fixtures = pd.merge(df_fixtures,df_db_awayteams, on='awayTeam_id')

    # with Fixture object
    for tu_fixture in df_fixtures.itertuples(index=False):
        fo = Fixture.objects.all().filter(api_id = tu_fixture.fixture_id)
        if fo.count() == 0:
            # Fixture does not yet exist in database => add
            league = League.objects.all().filter(id = tu_fixture.my_league_id).first()
            h_team = Team.objects.all().filter(id=tu_fixture.my_homeTeam_id).first()
            a_team = Team.objects.all().filter(id=tu_fixture.my_awayTeam_id).first()
            fnew = Fixture(api_id=tu_fixture.fixture_id, league=league, match_start=tu_fixture.dt_event_date, status=tu_fixture.status, status_short=tu_fixture.statusShort, home_team=h_team, away_team=a_team)
            if not pd.isna(tu_fixture.goalsHomeTeam):
                fnew.home_goals = int(tu_fixture.goalsHomeTeam)
            if not pd.isna(tu_fixture.goalsAwayTeam):
                fnew.away_goals = int(tu_fixture.goalsAwayTeam)
            if not pd.isna(tu_fixture.home_win):
                fnew.home_odds = tu_fixture.home_win
            if not pd.isna(tu_fixture.draw):
                fnew.draw_odds = tu_fixture.draw
            if not pd.isna(tu_fixture.away_win):
                fnew.away_odds = tu_fixture.away_win

            fnew.save()
        else:
            # Fixture exists, update relevant fields
            fo.update(match_start=tu_fixture.dt_event_date, status=tu_fixture.status, status_short=tu_fixture.statusShort)
            if not pd.isna(tu_fixture.goalsHomeTeam):
                fo.update(home_goals = int(tu_fixture.goalsHomeTeam))
            if not pd.isna(tu_fixture.goalsAwayTeam):
                fo.update(away_goals = int(tu_fixture.goalsAwayTeam))

            if mode == 'days': # Odds are only updated in the daily update, but not for live games or league updates
                if not pd.isna(tu_fixture.home_win):
                    fo.update(home_odds = tu_fixture.home_win)
                if not pd.isna(tu_fixture.draw):
                    fo.update(draw_odds = tu_fixture.draw)
                if not pd.isna(tu_fixture.away_win):
                    fo.update(away_odds = tu_fixture.away_win)
        
    fixture_update = UpdateSchedule.objects.all()
    fixture_update.update(last_fixture_update=make_aware(datetime.now())) # Make aware is neccesary because the field is timezone aware

    # after the fixture data is updated, the game scores are updated as well
    UpdateGameScores()

def scheduled_update():
    # This function should be called daily to update data from the API as required

    # Check if Leagues need to be updated
    schedule = UpdateSchedule.objects.all()
    lupdate = schedule.get() # Get data  from Queryset
    if date.today() >= lupdate.next_league_update:
        if update_leagues() > 0:
            # If a league as been added, teams need to be updated
            update_teams()
            update_fixtures(mode='leagues')
        schedule.update(next_league_update=date.today()+timedelta(days=7)) # schedule next update in a week

    # Check if fixtures need to be update (daily update)
    if date.today() >= lupdate.next_fixture_update:
        update_fixtures(mode='days')
        schedule.update(next_fixture_update=date.today()+timedelta(days=1)) # fixtures are updated daily
    
    
