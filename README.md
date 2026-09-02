# pi-pico-hc-sr04-ultrasonic

MicroPython project for reading distance from an HC-SR04 ultrasonic sensor using a Raspberry Pi Pico W.

## Hardware

- Raspberry Pi Pico W
- HC-SR04 ultrasonic distance sensor
- 1k ohm resistor

### Wiring

The HC-SR04 `Echo` pin outputs 5V, but the Pico's GPIO pins are only 3.3V tolerant. Wiring a 1k ohm resistor in series
with the `Echo` pin protects the GPIO input by limiting the current into its internal clamping diodes, which is a
simpler alternative to a full two-resistor voltage divider.

| HC-SR04 Pin | Pico W Pin                                 |
|-------------|--------------------------------------------|
| VCC         | VBUS (5V)                                  |
| GND         | GND                                        |
| Trig        | GPIO 21                                    |
| Echo        | GPIO 20 (in series with a 1k ohm resistor) |

These pin numbers match the defaults in `config.py` (`TRIGGER_PIN` and `ECHO_PIN`). If you wire the sensor to different
GPIO pins, edit `config.py` to match your wiring.

## Software

- [MicroPython](https://micropython.org/) firmware flashed to the Pico W
- Code in this repo copied to the device (e.g. with [Thonny](https://thonny.org/) or
[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html))

### Dependencies

This project uses the [`rsc1975/micropython-hcsr04`](https://github.com/rsc1975/micropython-hcsr04) driver for the
HC-SR04 sensor. Install it onto the device with
[`mpremote`](https://docs.micropython.org/en/latest/reference/mpremote.html), which fetches the file over your
computer's network connection and copies it straight to the Pico over USB &mdash; no manual download needed:

```bash
mpremote mip install github:rsc1975/micropython-hcsr04/hcsr04.py
```

If you have more than one MicroPython device connected, specify the serial port:

```bash
mpremote connect <port> mip install github:rsc1975/micropython-hcsr04/hcsr04.py
```

This installs `hcsr04.py` into `/lib` on the device. To confirm it's there:

```bash
mpremote fs ls lib
```

Distance readings will be sent to Prometheus (e.g. Grafana Cloud) via remote write, using the
[`ttk1/prometheus_remote_write_payload`](https://github.com/ttk1/prometheus_remote_write_payload) library. Install it
the same way:

```bash
mpremote mip install github:ttk1/prometheus_remote_write_payload
```

Metrics are sent over HTTPS using the
[`requests`](https://github.com/micropython/micropython-lib/tree/master/python-ecosys/requests) library, which is
already bundled with the MicroPython firmware used for this project.

### Configuration

Non-confidential settings such as GPIO pin numbers and the Prometheus metric name live in `config.py`, which is
committed to the repo:

| Name                           | Description                                                        | Default       |
|--------------------------------|--------------------------------------------------------------------|---------------|
| `TRIGGER_PIN`                  | GPIO pin connected to the HC-SR04 `Trig` pin                       | `21`          |
| `ECHO_PIN`                     | GPIO pin connected to the HC-SR04 `Echo` pin                       | `20`          |
| `METRIC_NAME`                  | Name of the Prometheus metric distance readings are sent under     | `distance_mm` |
| `SENSOR_LABEL`                 | Label identifying this sensor, attached to each metric sent        | `sensor_1`    |
| `SENSOR_POLL_INTERVAL_SECONDS` | How often the sensor is checked                                    | `5`           |
| `DISTANCE_CHANGE_THRESHOLD_MM` | How far (in mm) a reading must move to be treated as a real change | `15`          |
| `REQUIRED_STABLE_READINGS`     | Consecutive matching readings needed before a change is reported   | `3`           |

Edit `config.py` directly if your wiring differs from the defaults, or if you want to change the metric name or sensor
label.

Copy `secrets_example.py` to `secrets.py` and fill in your own values:

```bash
cp secrets_example.py secrets.py
```

`secrets.py` is ignored by git so your credentials won't be committed. It holds:

| Name                     | Description                                                             |
|--------------------------|-------------------------------------------------------------------------|
| `WIFI_SSID`              | Your WiFi network name                                                  |
| `WIFI_PASSWORD`          | Your WiFi network password                                              |
| `GRAFANA_CLOUD_ENDPOINT` | Your Grafana Cloud Prometheus remote write endpoint URL                 |
| `GRAFANA_CLOUD_AUTH`     | A `(username, api_token)` tuple: your Prometheus username and API token |

For `GRAFANA_CLOUD_ENDPOINT`, use your Grafana Cloud Prometheus remote write endpoint URL, e.g.
`https://prometheus-prod-24-prod-eu-west-2.grafana.net/api/prom/push`. You can find your endpoint URL, username and API
token on the Prometheus details page for your Grafana Cloud stack.

## Code

On startup, `main.py` connects to WiFi using the `WIFI_SSID` and `WIFI_PASSWORD` credentials from `secrets.py`. Once
connected, it fetches the current time from an NTP server and uses it to set the Pico's clock. This step is needed
because the Pico has no battery-backed real-time clock, so it always boots up with an incorrect time; the Prometheus
remote write library needs an accurate clock to timestamp the metrics it sends.

It then polls the HC-SR04 sensor every `SENSOR_POLL_INTERVAL_SECONDS`. Rather than sending a metric on every reading
(which would be noisy given how ultrasonic sensors jitter), it only reports a new distance once a reading has moved by
more than `DISTANCE_CHANGE_THRESHOLD_MM` from the last reported value, and that new value has then been seen
`REQUIRED_STABLE_READINGS` times in a row. This debouncing avoids false positives from momentary noise while still
reporting real changes (e.g. a car arriving in or leaving a parking space) promptly.

Each reported reading is sent to Grafana Cloud as a Prometheus remote write metric named `METRIC_NAME`, labelled with
`SENSOR_LABEL` so that readings from multiple Picos in different locations can be told apart in Grafana. The payload is
built with `PrometheusRemoteWritePayload` and POSTed to `GRAFANA_CLOUD_ENDPOINT` using `GRAFANA_CLOUD_AUTH` for
authentication.

## Deploying to the Device

Copy `main.py`, `config.py` and `secrets.py` onto the Pico W with `mpremote`:

```bash
mpremote fs cp main.py :main.py
mpremote fs cp config.py :config.py
mpremote fs cp secrets.py :secrets.py
```

If you have more than one MicroPython device connected, specify the serial port:

```bash
mpremote connect <port> fs cp main.py :main.py
mpremote connect <port> fs cp config.py :config.py
mpremote connect <port> fs cp secrets.py :secrets.py
```

## License

MIT &mdash; see [LICENSE](LICENSE).
