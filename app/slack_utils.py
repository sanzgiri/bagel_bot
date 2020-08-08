from typing import Any
from datetime import datetime as dt
import pandas as pd
from os import path
import streamlit as st


@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def get_channel_dict(session):
    channel_dict = {}
    response = session.conversations_list(limit=5000, exclude_archived=True)
    channels = response['channels']
    for channel in channels:
        channel_dict[channel['name']] = channel['id']
    return channel_dict


def get_user_df(session, channel_id):
    user_info_list: Any = []

    response = session.conversations_members(channel=channel_id, limit=100)
    user_list = response['members']
    for user in user_list:
        response = session.users_info(user=user, include_locale=True)
        user_info_list += [response['user']]

    user_df = pd.DataFrame(user_info_list)[['id', 'name', 'real_name', 'tz']]
    user_df = user_df[(~user_df.name.str.contains('donut')) &
                      (~user_df.name.str.contains('bagel'))].reset_index(drop=True)

    return user_df


def create_matches(user_df, history_file):

    if path.exists(history_file):
        history_df = pd.read_csv(history_file)
    else:
        history_df = pd.DataFrame()

    # Match across timezones and with those they haven't matched with yet
    possible_cases_df = pd.DataFrame(columns=['name1', 'name2', 'times_paired', 'is_diff_tz'])
    user_list = user_df['name'].tolist()

    for i in range(len(user_list)):
        name1 = user_df['name'][i]
        for j in range(i + 1, len(user_list)):
            name2 = user_df['name'][j]

            if len(history_df) > 0:
                tmp_hist_df = history_df[((history_df['name1'] == name1) &
                                          (history_df['name2'] == name2)) |
                                         ((history_df['name2'] == name1) &
                                          (history_df['name1'] == name2))]
                times_paired = len(tmp_hist_df)
            else:
                times_paired = 0

            name1_mask = user_df['name'].values == name1
            name2_mask = user_df['name'].values == name2

            name1_tz = user_df[name1_mask]['tz'].values[0]
            name2_tz = user_df[name2_mask]['tz'].values[0]

            is_diff_tz = (name1_tz != name2_tz)

            possible_cases_df = possible_cases_df.append({'name1': name1,
                                                          'name2': name2,
                                                          'times_paired': times_paired,
                                                          'is_diff_tz': is_diff_tz}, ignore_index=True)

    possible_cases_df['match_strength'] = (possible_cases_df['is_diff_tz'] * 2) - possible_cases_df['times_paired']
    filter_cases_df = possible_cases_df.copy(deep=True)

    match_df = pd.DataFrame(columns=['name1', 'name2'])
    ind = 0
    for user in user_df['name'].tolist():
        top_user_match = filter_cases_df[(filter_cases_df['name1'] == user) |
                                         (filter_cases_df['name2'] == user)].sort_values('match_strength',
                                                                                         ascending=False).reset_index(
            drop=True)[['name1', 'name2']].head(1).reset_index(drop=True)
        if len(top_user_match.index) > 0:
            name1 = top_user_match.name1.values[0]
            name2 = top_user_match.name2.values[0]
            match_df.loc[ind] = [name1, name2]
            filter_cases_df = filter_cases_df[(filter_cases_df['name1'] != name1) &
                                              (filter_cases_df['name2'] != name1)]
            filter_cases_df = filter_cases_df[(filter_cases_df['name1'] != name2) &
                                              (filter_cases_df['name2'] != name2)]
            ind += 1

    # Find if anyone wasn't matched, make a second match with their top option
    for user in user_df['name'].tolist():
        tmp_match_df = match_df[(match_df['name1'] == user) |
                                (match_df['name2'] == user)]
        if len(tmp_match_df.index) == 0:
            print(f'User: {user} was not matched. Setting a second match up for them...')
            top_user_match = possible_cases_df[(possible_cases_df['name1'] == user) |
                                               (possible_cases_df['name2'] == user)].sort_values('match_strength',
                                                                                                 ascending=False).reset_index(
                drop=True)[['name1', 'name2']].head(1).reset_index(drop=True)

            name1 = top_user_match.name1.values[0]
            name2 = top_user_match.name2.values[0]
            match_df.loc[ind] = [name1, name2]

    today = dt.strftime(dt.now(), "%Y-%m-%d")
    match_df['match_date'] = today

    return match_df


def update_history(match_df, history_file):

    if path.exists(history_file):
        history_df = pd.read_csv(history_file)
    else:
        history_df = pd.DataFrame()

    history_df = pd.concat([history_df, match_df])
    history_df.to_csv(history_file, index=False)


def post_matches(session, user_df, match_df, my_channel_id):

    for i in range(len(match_df)):
        user1 = match_df[match_df.index == i].name1.values[0]
        user2 = match_df[match_df.index == i].name2.values[0]
        user1_id = user_df[user_df['name'] == user1]['id'].values[0]
        user2_id = user_df[user_df['name'] == user2]['id'].values[0]
        response = session.conversations_open(users=[user1_id, user2_id], return_im=True)
        conv_id = response['channel']['id']
        response = session.chat_postMessage(channel=conv_id,
                                            text=f'Hello <@{user1_id}> and <@{user2_id}>! Welcome to a new round of Bagel-Bot! Please use this DM channel to set up time to connect!',
                                            as_user='@bagel-bot')

    # Send pairings to the ds_donut channel
    response = session.chat_postMessage(channel=my_channel_id,
                                            text='The new round of pairings are in! You should have received a DM from bagel-bot with your new Bagel partner. Please post a photo here of your chat. Chat, chat away!',
                                            as_user='@bagel_bot')
    for i in range(0, len(match_df.index)):
        user1 = match_df[match_df.index == i].name1.values[0]
        user2 = match_df[match_df.index == i].name2.values[0]
        user1_id = user_df[user_df['name'] == user1]['id'].values[0]
        user2_id = user_df[user_df['name'] == user2]['id'].values[0]
        response = session.chat_postMessage(channel=my_channel_id,
                                             text=f'<@{user1_id}> and <@{user2_id}>',
                                             as_user='@bagel-bot')
