import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

from exif_utils import extract_metadata

BOT_TOKEN = os.getenv("BOT_TOKEN", "8846679545:AAGYEUsOrFQOgfq30524DrEZYgniRDhrM4k")

MAX_FILE_SIZE = 20 * 1024 * 1024

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "send photo (file method) to read its metadata.\n"
    )


def _format_report(meta: dict) -> str:
    lines: list[str] = ["metadata\n"]

    file_part = []
    if meta.get("format"):
        file_part.append(meta["format"])
    if meta.get("width") and meta.get("height"):
        file_part.append(f"{meta['width']}×{meta['height']} px")
    if file_part:
        lines.append(f"file: {html.quote(' · '.join(map(str, file_part)))}")

    device = " ".join(str(x) for x in (meta.get("make"), meta.get("model")) if x).strip()
    if device:
        lines.append(f"device: {html.quote(device)}")
    if meta.get("lens"):
        lines.append(f"lens: {html.quote(str(meta['lens']))}")
    if meta.get("software"):
        lines.append(f"software: {html.quote(str(meta['software']))}")

    if meta.get("datetime"):
        lines.append(f"taken: {html.quote(str(meta['datetime']))}")

    shot = []
    if meta.get("fnumber"):
        shot.append(str(meta["fnumber"]))
    if meta.get("exposure"):
        shot.append(str(meta["exposure"]))
    if meta.get("iso"):
        shot.append(f"iso {meta['iso']}")
    if meta.get("focal_length"):
        shot.append(str(meta["focal_length"]))
    if shot:
        lines.append(f"shot: {html.quote(' · '.join(shot))}")
    if meta.get("flash"):
        lines.append(f"flash: {html.quote(str(meta['flash']))}")

    gps = meta.get("gps")
    if gps and "latitude" in gps:
        lat, lon = gps["latitude"], gps["longitude"]
        lines.append("")
        lines.append(f"coordinates: <code>{lat}, {lon}</code>")
        if gps.get("altitude") is not None:
            lines.append(f"altitude: {gps['altitude']} m")
        if gps.get("direction") is not None:
            lines.append(f"direction: {gps['direction']}°")
        if gps.get("gps_datetime_utc"):
            lines.append(f"gps time: {html.quote(gps['gps_datetime_utc'])}")
        lines.append(
            f'<a href="https://www.google.com/maps?q={lat},{lon}">open on map</a>'
        )
    else:
        lines.append("")
        lines.append("coordinates: not found")

    return "\n".join(lines)


@dp.message(F.document)
async def handle_document(message: Message, bot: Bot) -> None:
    document = message.document

    is_image = (document.mime_type or "").startswith("image/") or (
        document.file_name or ""
    ).lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp"))
    if not is_image:
        await message.answer("not an image. send a photo as a file.")
        return

    if document.file_size and document.file_size > MAX_FILE_SIZE:
        await message.answer("file is larger than 20 mb, telegram won't let me download it.")
        return

    status = await message.answer("reading metadata…")

    try:
        buf = await bot.download(document)
        data = buf.read()
        meta = extract_metadata(data)
    except Exception as exc:
        logging.exception("failed to process file")
        await status.edit_text(f"could not read file: {html.quote(str(exc))}")
        return

    await status.edit_text(_format_report(meta), disable_web_page_preview=True)


@dp.message(F.photo)
async def handle_compressed_photo(message: Message) -> None:
    await message.answer(
        "this is a compressed photo, telegram already stripped its exif.\n"
        "send the image as a file to keep the metadata."
    )


@dp.message()
async def fallback(message: Message) -> None:
    await message.answer("send photo (file method) to read its metadata.")


async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("Не задан BOT_TOKEN. Установите переменную окружения BOT_TOKEN.")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
