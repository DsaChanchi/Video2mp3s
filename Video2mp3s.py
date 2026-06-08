import os
import re
import inspect
import moviepy

from pytubefix import YouTube
from moviepy.audio.io.AudioFileClip import AudioFileClip


# ==================================================
# UTILIDADES
# ==================================================

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', "_", name).strip()
    return name[:200]


def sanitize_folder_name(name):
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()[:200]


def time_to_seconds(t):
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s


def crear_subclip(audio, inicio, fin):

    if hasattr(audio, "subclipped"):
        return audio.subclipped(inicio, fin)

    if hasattr(audio, "subclip"):
        return audio.subclip(inicio, fin)

    raise RuntimeError(
        f"MoviePy incompatible: {moviepy.__version__}"
    )


def guardar_audio(clip, destino):

    params = inspect.signature(
        clip.write_audiofile
    ).parameters

    kwargs = {}

    if "logger" in params:
        kwargs["logger"] = None

    if "verbose" in params:
        kwargs["verbose"] = False

    clip.write_audiofile(destino, **kwargs)


def on_progress(stream, chunk, bytes_remaining):

    total = getattr(stream, "filesize", None)

    if not total:
        return

    descargado = total - bytes_remaining
    porcentaje = (descargado / total) * 100

    print(
        f"\rDescargando audio: {porcentaje:6.2f}%",
        end="",
        flush=True
    )


# ==================================================
# INICIO
# ==================================================

print(f"MoviePy detectado: {moviepy.__version__}")

url = input("\nURL del vídeo: ").strip()

yt = YouTube(url, on_progress_callback=on_progress)

# ==================================================
# CARPETA DEL VÍDEO
# ==================================================

titulo_video = sanitize_folder_name(yt.title)

OUTPUT_DIR = os.path.join(os.getcwd(), titulo_video)
os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"\nVídeo: {yt.title}")
print(f"Carpeta: {OUTPUT_DIR}")

# ==================================================
# DETECCIÓN DE CAPÍTULOS O INPUT MANUAL
# ==================================================

segments = []

print("\nBuscando capítulos...")

try:
    chapters = yt.chapters

    if chapters and len(chapters) > 0:

        for ch in chapters:
            segments.append({
                "start": int(ch.start_seconds),
                "title": ch.title.strip()
            })

        segments.sort(key=lambda x: x["start"])

        print(f"Capítulos encontrados: {len(segments)}\n")

        for s in segments:
            h = s["start"] // 3600
            m = (s["start"] % 3600) // 60
            sec = s["start"] % 60

            print(f"{h:02d}:{m:02d}:{sec:02d} - {s['title']}")

    else:
        raise Exception()

except Exception:

    print("\nNo hay capítulos. Usando entrada manual.\n")
    print("Formato: HH:MM:SS - Texto")
    print("Escribe FIN para terminar.\n")

    lines = []

    while True:
        line = input()
        if line.strip().upper() == "FIN":
            break
        lines.append(line)

    for line in lines:

        if " - " not in line:
            continue

        try:
            t, txt = line.split(" - ", 1)

            segments.append({
                "start": time_to_seconds(t.strip()),
                "title": txt.strip()
            })

        except:
            pass

if not segments:
    raise Exception("No hay segmentos válidos.")

segments.sort(key=lambda x: x["start"])

# ==================================================
# DESCARGA AUDIO
# ==================================================

stream = (
    yt.streams
    .filter(only_audio=True)
    .order_by("abr")
    .desc()
    .first()
)

audio_path = stream.download(
    output_path=OUTPUT_DIR,
    filename="audio_original"
)

print("\nDescarga completada.")

# ==================================================
# DURACIÓN
# ==================================================

audio = AudioFileClip(audio_path)
duration = audio.duration
audio.close()

print(f"Duración: {duration:.2f}s")

# ==================================================
# GENERAR MP3
# ==================================================

print("\nGenerando MP3...\n")

total = len(segments)

for i, seg in enumerate(segments):

    start = seg["start"]

    if i < total - 1:
        end = segments[i + 1]["start"]
    else:
        end = duration

    name = sanitize_filename(seg["title"]) + ".mp3"
    path = os.path.join(OUTPUT_DIR, name)

    audio_clip = None
    clip = None

    try:
        audio_clip = AudioFileClip(audio_path)
        clip = crear_subclip(audio_clip, start, end)
        guardar_audio(clip, path)

    finally:
        try:
            if clip:
                clip.close()
            if audio_clip:
                audio_clip.close()
        except:
            pass

    print(f"[{i+1}/{total}] {name}")

# ==================================================
# LIMPIEZA
# ==================================================

try:
    os.remove(audio_path)
    print("\nAudio temporal eliminado.")
except:
    pass

print("\n✔ Proceso completado")
print("Carpeta:", OUTPUT_DIR)
