import time

import network
import ntptime
import requests
from hcsr04 import HCSR04
from prometheus_remote_write_payload import PrometheusRemoteWritePayload

from config import (
    TRIGGER_PIN,
    ECHO_PIN,
    METRIC_NAME,
    SENSOR_LABEL,
    SENSOR_POLL_INTERVAL_SECONDS,
    DISTANCE_CHANGE_THRESHOLD_MM,
    REQUIRED_STABLE_READINGS,
)
from secrets import WIFI_SSID, WIFI_PASSWORD, GRAFANA_CLOUD_ENDPOINT, GRAFANA_CLOUD_AUTH


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    while not wlan.isconnected():
        time.sleep(1)

    print("Connected, IP address:", wlan.ifconfig()[0])


def set_ntp_time():
    got_time = False

    print("Getting network time...")

    while not got_time:
        try:
            ntptime.settime()
            got_time = True
        except OSError:
            print("Failed to set NTP time, retrying...")
            time.sleep(.5)

    print("Network time set.")


def send_metric(distance_mm):
    print("Sending metric:", METRIC_NAME, "=", distance_mm, "label:", SENSOR_LABEL)

    payload = PrometheusRemoteWritePayload()
    payload.add_data(
        METRIC_NAME, {"sensor": SENSOR_LABEL}, distance_mm, time.time() * 1000
    )

    response = requests.post(
        GRAFANA_CLOUD_ENDPOINT,
        headers={
            "Content-Encoding": "snappy",
            "Content-Type": "application/x-protobuf",
            "User-Agent": "pi-pico-hc-sr04-ultrasonic",
            "X-Prometheus-Remote-Write-Version": "1.0.0",
        },
        auth=GRAFANA_CLOUD_AUTH,
        data=payload.get_payload(),
    )

    print(response.status_code)
    print(response.text)
    response.close()


def monitor_distance():
    sensor = HCSR04(trigger_pin=TRIGGER_PIN, echo_pin=ECHO_PIN)

    last_sent_distance = None
    candidate_distance = None
    candidate_count = 0

    while True:
        try:
            distance = sensor.distance_mm()
        except OSError:
            print("Sensor reading timed out, skipping.")
            time.sleep(SENSOR_POLL_INTERVAL_SECONDS)
            continue

        if last_sent_distance is None:
            last_sent_distance = distance
            send_metric(distance)
        elif abs(distance - last_sent_distance) > DISTANCE_CHANGE_THRESHOLD_MM:
            if candidate_distance is not None and abs(distance - candidate_distance) <= DISTANCE_CHANGE_THRESHOLD_MM:
                candidate_count += 1
            else:
                candidate_distance = distance
                candidate_count = 1

            if candidate_count >= REQUIRED_STABLE_READINGS:
                last_sent_distance = candidate_distance
                send_metric(candidate_distance)
                candidate_distance = None
                candidate_count = 0
        else:
            candidate_distance = None
            candidate_count = 0

        time.sleep(SENSOR_POLL_INTERVAL_SECONDS)


connect_wifi()
set_ntp_time()
monitor_distance()
