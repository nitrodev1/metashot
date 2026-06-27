# geoint

![python](https://img.shields.io/badge/python-3.10+-3776ab) ![aiogram](https://img.shields.io/badge/aiogram-3.29-2ca5e0) ![pillow](https://img.shields.io/badge/pillow-12-92c) ![license](https://img.shields.io/badge/license-mit-black)

a telegram bot that reads photo metadata. send a photo as a file and it
extracts everything it can from the exif: coordinates, device, capture time
and camera settings.

## why file method

sent as a compressed photo, telegram strips the exif. sent as a file the
metadata stays intact.

## features

- gps coordinates, altitude, direction + google maps link
- device make / model, lens, software
- capture time
- shot settings: aperture, exposure, iso, focal length, flash
- heic / heif support (iphone photos)

## install

```bash
pip install -r requirements.txt
```

## run

```bash
export BOT_TOKEN="your-token-from-botfather"
python bot.py
```

on windows (cmd):

```bat
set BOT_TOKEN=your-token-from-botfather
py bot.py
```

## usage

1. open the bot, send `/start`
2. attach a photo as a file (file method, not as a photo)
3. get the metadata back

## layout

```
bot.py           handlers and message formatting
exif_utils.py    exif parsing
requirements.txt dependencies
```


