FROM python:3.7.2-stretch

RUN pip install streamlit typing slackclient
EXPOSE 8501

RUN mkdir -p /root/.streamlit
COPY app/config.toml /root/.streamlit/config.toml
COPY app/credentials.toml /root/.streamlit/credentials.toml

COPY . /app_bagel-bot
WORKDIR /app_bagel-bot

CMD streamlit run app/bagel_bot.py --server.enableCORS=false --server.headless=false

