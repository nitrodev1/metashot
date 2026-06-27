from __future__ import annotations

from datetime import datetime
from fractions import Fraction
from io import BytesIO

from PIL import Image, ExifTags

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

_TAGS = ExifTags.TAGS
_GPSTAGS = ExifTags.GPSTAGS


def _to_float(value) -> float | None:
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, Fraction):
            return float(value)
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _dms_to_decimal(dms, ref) -> float | None:
    try:
        deg = _to_float(dms[0])
        minutes = _to_float(dms[1])
        seconds = _to_float(dms[2])
        if None in (deg, minutes, seconds):
            return None
        decimal = deg + minutes / 60.0 + seconds / 3600.0
        if ref in ("S", "W"):
            decimal = -decimal
        return round(decimal, 6)
    except (TypeError, IndexError):
        return None


def _parse_gps(gps_ifd: dict) -> dict:
    gps = {_GPSTAGS.get(k, k): v for k, v in gps_ifd.items()}
    result: dict = {}

    lat = gps.get("GPSLatitude")
    lat_ref = gps.get("GPSLatitudeRef")
    lon = gps.get("GPSLongitude")
    lon_ref = gps.get("GPSLongitudeRef")

    if lat and lon and lat_ref and lon_ref:
        latitude = _dms_to_decimal(lat, lat_ref)
        longitude = _dms_to_decimal(lon, lon_ref)
        if latitude is not None and longitude is not None:
            result["latitude"] = latitude
            result["longitude"] = longitude

    altitude = gps.get("GPSAltitude")
    if altitude is not None:
        alt = _to_float(altitude)
        if alt is not None:
            if gps.get("GPSAltitudeRef") in (1, b"\x01"):
                alt = -alt
            result["altitude"] = round(alt, 2)

    if gps.get("GPSImgDirection") is not None:
        direction = _to_float(gps.get("GPSImgDirection"))
        if direction is not None:
            result["direction"] = round(direction, 1)

    gps_date = gps.get("GPSDateStamp")
    gps_time = gps.get("GPSTimeStamp")
    if gps_date and gps_time:
        try:
            h, m, s = (int(_to_float(x) or 0) for x in gps_time)
            result["gps_datetime_utc"] = f"{gps_date} {h:02d}:{m:02d}:{s:02d} UTC"
        except (TypeError, ValueError):
            pass

    return result


def _format_datetime(raw: str) -> str:
    try:
        dt = datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    except (ValueError, TypeError):
        return raw


def extract_metadata(data: bytes) -> dict:
    info: dict = {}

    with Image.open(BytesIO(data)) as img:
        info["format"] = img.format
        info["mode"] = img.mode
        info["width"], info["height"] = img.size

        exif = img.getexif()
        if not exif:
            return info

        flat = {_TAGS.get(k, k): v for k, v in exif.items()}

        info["make"] = flat.get("Make")
        info["model"] = flat.get("Model")
        info["software"] = flat.get("Software")
        info["orientation"] = flat.get("Orientation")

        dt = flat.get("DateTimeOriginal") or flat.get("DateTime") or flat.get("DateTimeDigitized")
        if dt:
            info["datetime"] = _format_datetime(str(dt))

        try:
            exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
        except Exception:
            exif_ifd = {}
        exif_flat = {_TAGS.get(k, k): v for k, v in exif_ifd.items()}

        if not info.get("datetime"):
            dt2 = exif_flat.get("DateTimeOriginal") or exif_flat.get("DateTimeDigitized")
            if dt2:
                info["datetime"] = _format_datetime(str(dt2))

        info["lens"] = exif_flat.get("LensModel")

        exposure = exif_flat.get("ExposureTime")
        if exposure is not None:
            val = _to_float(exposure)
            if val:
                info["exposure"] = f"{Fraction(val).limit_denominator(8000)} s" if val < 1 else f"{val:g} s"

        fnumber = exif_flat.get("FNumber")
        if fnumber is not None:
            val = _to_float(fnumber)
            if val:
                info["fnumber"] = f"f/{val:g}"

        iso = exif_flat.get("ISOSpeedRatings") or exif_flat.get("PhotographicSensitivity")
        if iso is not None:
            info["iso"] = iso if not isinstance(iso, (tuple, list)) else iso[0]

        focal = exif_flat.get("FocalLength")
        if focal is not None:
            val = _to_float(focal)
            if val:
                info["focal_length"] = f"{val:g} mm"

        flash = exif_flat.get("Flash")
        if flash is not None:
            try:
                info["flash"] = "fired" if int(flash) & 1 else "did not fire"
            except (TypeError, ValueError):
                pass

        try:
            gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
        except Exception:
            gps_ifd = {}
        if gps_ifd:
            gps = _parse_gps(gps_ifd)
            if gps:
                info["gps"] = gps

    return {k: v for k, v in info.items() if v not in (None, "", {})}
