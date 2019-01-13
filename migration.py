

import pyodbc
import pymongo
import collections
from bokeh.io import show, output_file
from bokeh.plotting import figure
from bokeh.models import Select
from bokeh.layouts import row, column
from bokeh.io import curdoc
from datetime import datetime
from bokeh.io import output_file, show
from bokeh.layouts import widgetbox
from bokeh.models.widgets import Select
from bokeh.models import CustomJS


def connect():
    # Specifying the ODBC driver, server name, database, etc. directly
    cnxn = pyodbc.connect('DRIVER={MySQL ODBC 5.3 UNICODE Driver};SERVER=localhost;DATABASE=all_beters;uid=root')
    # Create a cursor from the connection
    return cnxn.cursor()


def connect_mongo():
    my_client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = my_client["admin"]
    return db


def insert_leagues(cursor, mongo_client):
    unique_leagues = collections.defaultdict(int)
    leagues_to_insert = []

    # Fetch records
    cursor.execute("SELECT league, sport_id FROM vaja")
    leagues_res = cursor.fetchall()

    # build unique league documents

    for lg in leagues_res:
        unique_league_key = lg[0]
        unique_leagues[unique_league_key] += 1
        if unique_leagues[unique_league_key] == 1:
            leagues_to_insert.append({'Name': unique_league_key, 'Sport':lg[1]})

    # insert leagues
    mongo_client.leagues.insert_many(leagues_to_insert)


def get_leagues_map(mongo_client):
    league_map = {}  # holding ids from Mongo
    # get leagues with id and build map
    for doc in mongo_client.leagues.find():
        league_map[doc['Name']] = doc['_id']
    return league_map


def get_match_map(mongo_client):
    match_map = {}
    # get matches with ids and put them into map
    for doc in mongo_client.matches.find():
        mkey = str(doc["Liga"])+ doc["Ekipa1"]+ doc["Ekipa2"]+ str(doc["Date"])
        match_map[mkey] = doc["_id"]
    return match_map


def get_match_key_unique(league_map, match_row):
    return str(league_map[match_row[6]]) + match_row[7] + match_row[8] + str(match_row[9])


def insert_mathes(cursor, mongo_client, league_map):

    match_list = []
    unique_match_map = collections.defaultdict(int)

    # Fetch records for matches
    cursor.execute("SELECT * FROM vaja");
    records = cursor.fetchall();

    # Now we have id for leagues, prepare matches with league ids
    for row in records:
        unique_match_key = get_match_key_unique(league_map, row)
        unique_match_map[unique_match_key] += 1
        # if there is only one record of this type, then we can inserts this. (Do not duplicate)
        if unique_match_map[unique_match_key] == 1:
            match_list.append(
                {"Liga": league_map[row[6]], "Ekipa1": row[7], "Ekipa2": row[8], "Date": row[9], "Score": row[18]})

    # insert matches
    mongo_client.matches.insert_many(match_list)


def insert_bets(cursor, mongo_client, league_map, match_map, options_map, bet_type_map):
    # holding bets
    bets_to_insert = []
    # Fetch records for matches
    cursor.execute("SELECT * FROM vaja");
    records = cursor.fetchall();

    # build bet record
    for bet in records:
        match_id = match_map[get_match_key_unique(league_map, bet)]  # get match id from mongo
        options_id = options_map[get_option_key(bet)]
        bet_type_id = bet_type_map[get_bet_type_key(bet)]
        bets_to_insert.append({
            "BetterId": bet[1],
            "Match": match_id,
            "Options": options_id,
            "BetType": bet_type_id,
            "PickedQuota": float(bet[16]),
            "PickedOption": bet[17],
            "Status": bet[19],
        })

    mongo_client.bets.insert_many(bets_to_insert)


def insert_options(cursor, mongo_client):
    # holding records to insert
    options_to_insert = []
    # Fetch records for matches
    cursor.execute("SELECT options1, options2, options3 FROM all_beters.vaja group by options1, options2, options3")
    records = cursor.fetchall()

    for opt in records:
        options_to_insert.append({
            "Option1": opt[0],
            "Option2": opt[1],
            "Option3": opt[2],
        })

    mongo_client.bet_options.insert_many(options_to_insert)


def insert_bet_percentage(cursor, mongo_client, league_map, match_map, bet_type_map):
    # holding records to insert
    percentages_to_insert = []
    unique_perc_records = collections.defaultdict(int)
    # Fetch records for matches
    cursor.execute("SELECT * FROM all_beters.vaja")
    records = cursor.fetchall()

    for row in records:
        match_id = match_map[get_match_key_unique(league_map, row)]  # get match id from mongo
        bet_type_id = bet_type_map[get_bet_type_key(row)]
        unique_percentage_key = str(match_id) + str(bet_type_id)
        unique_perc_records[unique_percentage_key] += 1
        # insert only one record for one percentage
        if unique_perc_records[unique_percentage_key] == 1:
            percentages_to_insert.append({
                "MatchId": match_id,
                "BetTypeId": bet_type_id,
                "Percentage1": row[10],
                "Percentage2": row[11],
                "Percentage3": row[12],
            })

    mongo_client.bet_percents.insert_many(percentages_to_insert)


def insert_bet_types(cursor, mongo_client):
    # holding records to insert
    types_to_insert = []
    # Fetch records for types
    cursor.execute("SELECT type1_id, type2, type3 FROM all_beters.vaja group by type1_id, type2, type3")
    records = cursor.fetchall()

    for type_bet in records:
        types_to_insert.append({
            "Type1": type_bet[0],
            "Type2": type_bet[1],
            "Type3": type_bet[2],
        })

    mongo_client.bet_types.insert_many(types_to_insert)


def get_option_key(bet_row):
    return bet_row[13]+bet_row[14]+bet_row[15]


def get_bet_type_key(bet_row):
    return str(bet_row[3])+bet_row[4]+bet_row[5]


def get_option_map(mongo_client):
    # holding option map
    option_map_id = {}
    # get all options
    for doc in mongo_client.bet_options.find():
        opt_key = doc["Option1"] + doc["Option2"]+ doc["Option3"]
        option_map_id[opt_key] = doc["_id"]
    return option_map_id


def get_type_map(mongo_client):
    # holding option map
    option_map_id = {}
    # get all options
    for doc in mongo_client.bet_types.find():
        type_key = str(doc["Type1"]) + doc["Type2"] + doc["Type3"]
        option_map_id[type_key] = doc["_id"]
    return option_map_id


def migrate(cursor,mongo_client):

    # Insert leagues
    insert_leagues(cursor, mongo_client)
    leagues_map = get_leagues_map(mongo_client)  # map with populated ids

    # Insert matches
    insert_mathes(cursor, mongo_client, leagues_map)
    match_map = get_match_map(mongo_client)  # map with populated ids

    # Insert bet options
    insert_options(cursor, mongo_client)
    options_map = get_option_map(mongo_client)  # map with populated ids

    # Insert bet types
    insert_bet_types(cursor,mongo_client)
    bet_type_map = get_type_map(mongo_client)  # map with populated ids

    # Insert bets
    insert_bets(cursor, mongo_client, leagues_map, match_map, options_map,bet_type_map)

    # Insert bets percentages
    insert_bet_percentage(cursor, mongo_client, leagues_map, match_map, bet_type_map)


def get_number_of_bets_correlated_to_sport_id_dict():
    query = [{'$lookup':{'from':'matches','localField':'Match','foreignField':'_id','as':'match'}},
             {'$lookup':{'from':'leagues','localField':'match.Liga','foreignField':'_id','as':'Liga'}}]
    joined_bet_match_league = mongo_client.bets.aggregate(query)
    dict_sport_bets = {}
    for i in joined_bet_match_league:
        if not i['Liga'][0]['Sport'] in dict_sport_bets:
            dict_sport_bets[i['Liga'][0]['Sport']] = 1
        else:
            dict_sport_bets[i['Liga'][0]['Sport']] = dict_sport_bets[i['Liga'][0]['Sport']] + 1
    return dict_sport_bets


def visualize_sports_bets():
    b_dict = get_number_of_bets_correlated_to_sport_id_dict()
    output_file("bets_sports.html")
    sports = {21:'Rokomet',
              28:'Plavanje',
              11:'Košarka',
              15:'Šah',
              8:'Floorball',
              29:'Tek',
              27:'Nogomet',
              10:'Snooker',
              20:'Skoki',
              25:'Smučanje',
              24:'Pikado',
              30:'Curling',
              6:'Biljard'}

    p = figure(x_range=list(sports.values()), plot_height=350, title="Število stav na posamezen šport",
               toolbar_location=None, tools="")
    p.vbar(x=list(sports.values()), top=list(b_dict.values()), width=0.9)
    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    show(p)


def get_days_profit_dict():
    query = [{'$lookup':{'from':'matches','localField':'Match','foreignField':'_id','as':'match'}},
             {'$lookup':{'from':'leagues','localField':'match.Liga','foreignField':'_id','as':'Liga'}}]
    joined_bet_match_league = mongo_client.bets.aggregate(query)
    dict_day_profit = {}
    single_bet_investment = 1
    for row in joined_bet_match_league:
        status = row["Status"]
        quota  = row["PickedQuota"]
        bet_date = str(row['match'][0]['Date'])
        datetime_object = datetime.strptime(bet_date, '%Y-%m-%d %H:%M:%S')
        key_date = '{:%m-%d-%Y}'.format(datetime_object)
        if datetime_object.year ==  datetime.strptime('2018', '%Y').year:
            continue
        if key_date not in dict_day_profit:
            dict_day_profit[key_date] = quota*single_bet_investment if status == "W" else -single_bet_investment
        else:
            dict_day_profit[key_date] = dict_day_profit[key_date] + quota*single_bet_investment if status == "W" else dict_day_profit[key_date] - single_bet_investment
    return dict_day_profit

def visualize_day_profit():
    p_dict = get_days_profit_dict()
    output_file("days_profits.html")
    date_time_days = [datetime.strptime(k, '%m-%d-%Y') for k in p_dict.keys()]
    p = figure(x_axis_type='datetime', plot_height=550, plot_width=950, title="Dobiček na posamezen dan",
               toolbar_location="right", )
    p.vbar(x=date_time_days, top=list(p_dict.values()), width=3)
    p.xgrid.grid_line_color = None
    p.y_range.start = -100
    show(p)

def get_sport_type_bets():
    query = [{'$lookup':{'from':'matches','localField':'Match','foreignField':'_id','as':'match'}},
             {'$lookup':{'from':'leagues','localField':'match.Liga','foreignField':'_id','as':'Liga'}},
             {'$lookup':{'from':'bet_types','localField':'BetType','foreignField':'_id','as':'bet_type'}}
             ]
    joined_bet_match_league_type = mongo_client.bets.aggregate(query)
    dict_sport = {}
    for row in joined_bet_match_league_type:
        sport_id = row["Liga"][0]["Sport"]
        type     = row["bet_type"][0]["Type1"]

        if sport_id not in dict_sport:
            dict_sport[sport_id] = {}
        else:
            if type not in dict_sport[sport_id]:
                dict_sport[sport_id][type] = 1
            else:
                dict_sport[sport_id][type] = dict_sport[sport_id][type] + 1
    return  dict_sport
    #for k,v in dict_sport.items():
    #    print(str(k) + " : " + str(v))
    #21 : {2: 60, 12: 996, 8: 53, 3: 31, 9: 1}
    #28 : {9: 3, 3: 5, 12: 6}
    #11 : {9: 18, 3: 164, 12: 4055, 2: 6, 8: 12}
    #15 : {9: 1}
    #8 : {9: 9}
    #29 : {9: 7}
    #27 : {12: 9225, 2: 144, 6: 4, 3: 60, 7: 7, 8: 190, 4: 11, 10: 3, 9: 1}
    #10 : {12: 395, 3: 2}
    #20 : {12: 290, 3: 14, 2: 1, 8: 1}
    #25 : {2: 2, 12: 108, 3: 5, 8: 2}
    #24 : {8: 2, 12: 81, 3: 3}
    #30 : {}
    #6 : {12: 9}

def visualize_sport_type(sport_id):
    p_dict = get_sport_type_bets()
    output_file("bet_types.html")
    bettype_number = p_dict[sport_id]
    p = figure(x_range=[str(k) for k in bettype_number.keys()], plot_height=350, title="Tip stave na šport: " + str(sport_id),
               toolbar_location="right", )
    p.vbar(x=[str(k) for k in bettype_number.keys()],top=list(bettype_number.values()), width=0.9)
    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    #show(p)

    city_select = Select(value=str(sport_id), title='Sport id', options=[str(k) for k in p_dict.keys()])

    def update_plot(attrname, old, new):
        city = city_select.value
        p = figure(x_range=[str(k) for k in bettype_number.keys()], plot_height=350, title="Tip stave na šport: " + str(sport_id),
               toolbar_location="right", )
        p.vbar(x=[str(k) for k in bettype_number.keys()],top=list(bettype_number.values()), width=0.9)

    #city_select.on_change('value', update_plot)
    controls = column(city_select)
    show(row(p, controls))




if __name__ == '__main__':
    #cursor = connect()
    mongo_client = connect_mongo()
    visualize_sport_type(21)











