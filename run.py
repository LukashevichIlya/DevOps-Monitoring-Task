import logging
import time
import graphyte

from selenium import webdriver
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import tz

logging.getLogger().setLevel(logging.INFO)

BASE_URL = 'https://yandex.ru/pogoda/kaliningrad'


def find_temp_in_hour(page):
    today = datetime.today()
    day_start = datetime(today.year, today.month, today.day, tzinfo=tz.tzlocal()).astimezone(
        tz.gettz('Russia/Kaliningrad')).timestamp()
    hourly_weather_blocks = page.findAll('div', {'class': 'fact__hour-temp'})
    hourly_label_blocks = page.findAll('div', {'class': 'fact__hour-label'})

    allowed_start_temp = ['+', '-', '0']
    allowed_start_time = ['0', '1', '2', '3', '4', '5', '6', ' 7', '8', '9']

    first_time = hourly_label_blocks[1].get_text()
    first_temp = hourly_weather_blocks[1].get_text()
    if first_temp[0] in allowed_start_temp:
        if first_time[0] not in allowed_start_time:
            day_start += 3600 * 24
            first_time = '00:00'
        time_in_seconds = int(first_time[:first_time.find(':')]) * 3600
        forecast_timestamp = day_start + time_in_seconds
        return int(first_temp[0:first_temp.find('°')]), forecast_timestamp
    else:
        second_time = hourly_label_blocks[2].get_text()
        second_temp = hourly_weather_blocks[2].get_text()
        time_in_seconds = int(second_time[:second_time.find(':')]) * 3600
        forecast_timestamp = day_start + time_in_seconds
        return int(second_temp[0:second_temp.find('°')]), forecast_timestamp


def find_current_temp(page):
    current_temp = int(page.find(string='Текущая температура').findParent().find_next().get_text())
    return current_temp


GRAPHITE_HOST = 'graphite'


def send_forecast_metric(weather, timestamp):
    sender = graphyte.Sender(GRAPHITE_HOST, prefix='yandex_weather')
    sender.send('forecast.temp', weather, time.time() + 30)


def send_current_metric(current_temp):
    sender = graphyte.Sender(GRAPHITE_HOST, prefix='yandex_weather')
    sender.send('current.temp', current_temp)


def main():
    driver = webdriver.Remote(
        command_executor='http://selenium:4444/wd/hub',
        desired_capabilities={'browserName': 'chrome', 'javascriptEnabled': True}
    )

    driver.get(BASE_URL)
    time.sleep(5)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    forecast_temp, timestamp = find_temp_in_hour(soup)
    send_forecast_metric(forecast_temp, timestamp)
    current_temp = find_current_temp(soup)
    send_current_metric(current_temp)

    driver.quit()

    logging.info('Accessed %s ..', BASE_URL)


if __name__ == '__main__':
    main()

