# datasheet — vendor datasheets for the on-board parts

![Doc Type](https://img.shields.io/badge/doc-datasheets-blue)
![Platform](https://img.shields.io/badge/platform-Propeller%202-blue)
![Maintainer](https://img.shields.io/badge/maintainer-stephen%40ironsheep.biz-blue?labelColor=black)
![License](https://img.shields.io/badge/license-MIT-green)

Manufacturer datasheets for the silicon on the Robot Dog connection board, kept locally
so the register-level details are at hand while writing the P2 drivers. Device roles and
I²C addresses are summarized in [`../RPI_GPIO_USAGE.md`](../RPI_GPIO_USAGE.md) and the
top-level [`CLAUDE.md`](../../CLAUDE.md).

| File | Part | Role in this build |
|------|------|--------------------|
| [`PCA9685.pdf`](PCA9685.pdf) | NXP PCA9685 | 16-channel PWM @ 50 Hz, I²C `0x40` — drives the 13 servos (12 leg joints + head). |
| [`ADS7830.pdf`](ADS7830.pdf) | TI ADS7830 | 8-channel 8-bit ADC, I²C `0x48` — battery voltage on ch 0 (÷3 divider). |
| [`mpu-6050_datasheet_v3 4.pdf`](mpu-6050_datasheet_v3%204.pdf) | InvenSense MPU-6050 | 6-axis IMU, I²C `0x68` — balance / attitude. |
| [`WS2812.pdf`](WS2812.pdf) | WorldSemi WS2812 | Addressable RGB LEDs (7-px ring) on GPIO18 / P8. |
| [`28029-Smart-Sensors-Text-v1.0.pdf`](28029-Smart-Sensors-Text-v1.0.pdf) | Parallax #28029 | Smart-Sensors text — ultrasonic ranging (HC-SR04-style TRIG/ECHO) background. |

> These PDFs are **third-party manufacturer documents**, redistributed here only as a
> convenience for development. Each remains the copyright of its respective vendor and is
> **not** covered by this project's MIT license.

---

## License

MIT License - See [LICENSE](../../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
