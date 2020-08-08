from os import path
import time
import streamlit as st
from slack import WebClient
from slack.errors import SlackApiError
import slack_utils as su
from SessionState import get

version_file = "/app_bagel-bot/app/_version.py"
bagel_token = "xxxxxxxxxx"
my_session = WebClient(token=bagel_token)
history_dir = "/data/bagel_history/"
debug = 0

def main():

    # read in version information
    version_dict = {}
    with open(version_file) as file:
        exec(file.read(), version_dict)

    # Create the title
    st.markdown(f"""<div style="font-size:5pt; font-weight:100; text-align:center; width=100%;">
                    <span style="font-size:40pt;">{version_dict['__project__']}</span><br>
                    <span style="font-size:15pt; color:#a1a1a1;">{version_dict['__description__']} 
                        (v {version_dict['__version__']})</span></div>""", unsafe_allow_html=True)

    # get channel_dict and cache it
    # st.write('Generating channel dictionary...')
    # channel_dict = su.get_channel_dict(my_session)

    # to improve performance, provide a static dict with channel names and ids
    my_channel_dict = \
                       {'Select channel:': '',
                       'bagel_test': 'XXXXXXXX',
                       'dunkin-bagel': 'YYYYYYYY',
                       'lox-bagel': 'ZZZZZZZZ'}

    # get channel from UI dropdown
    st.text("\n\n\n")
    my_channel = st.selectbox('Select channel with bagel users:', tuple(my_channel_dict.keys()), index=0)

    post_matches = st.checkbox('Post Matches')

    if st.button('Generate Matches'):

        if (my_channel != 'Select channel:'):

            my_channel_id = my_channel_dict[my_channel]

            # history file to persist
            my_history_file = f"{history_dir}{my_channel}_history.csv"

            st.write(f"Getting users in {my_channel} channel...")
            my_user_df = su.get_user_df(my_session, my_channel_id)
            num_users = len(my_user_df)
            st.write(f"{num_users} users found!")

            st.write(f"Generating optimal matches, this could take some time...")
            match_df = su.create_matches(my_user_df, my_history_file)

            st.write("The following matches have been generated:")
            st.write(match_df)

            if post_matches:
                st.write(f"Posting matches to {my_channel} channel.")
                st.write("Setting up DM channels for matched pairs.")
                su.post_matches(my_session, my_user_df, match_df, my_channel_id)

                st.write("Updating history.")
                su.update_history(match_df, my_history_file)

            st.write("Done!")
            st.write("Thanks for using Bagel Bot! Goodbye!")

        else:
            st.write("Please select a channel!")


if __name__ == '__main__':

    session_state = get(password='')

    if session_state.password != 'T0p_S3cr3t':
        pwd_placeholder = st.sidebar.empty()
        pwd = pwd_placeholder.text_input("Password:", value="", type="password")
        session_state.password = pwd
        if session_state.password == 'pwd123':
            pwd_placeholder.empty()
            main()
        elif session_state.password != '':
            st.error("the password you entered is incorrect")
    else:
        main()

