import os
import re
import inspect
import moviepy

from pytubefix import YouTube
from moviepy.audio.io.AudioFileClip import AudioFileClip


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
        f"Método de corte no encontrado. "
        f"MoviePy {moviepy.__version__}"
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

    clip.write_audiofile(
        destino,
        **kwargs
    )


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

# ==================================================
# LISTA DE TIEMPOS
# ==================================================

print("\nPega la lista completa.")
print("Formato: HH:MM:SS - Texto")
print("Escribe FIN para terminar.\n")

lines = []

while True:

    line = input()

    if line.strip().upper() == "FIN":
        break

    lines.append(line)

segments = []

for line in lines:

    line = line.strip()

    if not line:
        continue

    if " - " not in line:
        print(f"Línea ignorada: {line}")
        continue

    try:

        tiempo, texto = line.split(" - ", 1)

        segments.append({
            "start": time_to_seconds(
                tiempo.strip()
            ),
            "title": texto.strip()
        })

    except Exception:
        print(f"Línea ignorada: {line}")

if not segments:
    raise Exception(
        "No se encontraron segmentos válidos."
    )

segments.sort(
    key=lambda x: x["start"]
)

# ==================================================
# YOUTUBE
# ==================================================

print()

yt = YouTube(
    url,
    on_progress_callback=on_progress
)

titulo_video = sanitize_folder_name(
    yt.title
)

OUTPUT_DIR = os.path.join(
    os.getcwd(),
    titulo_video
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

print(f"Vídeo detectado: {yt.title}")
print(f"Carpeta destino: {OUTPUT_DIR}")

# ==================================================
# DESCARGA
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
print("Archivo:", audio_path)

# ==================================================
# DURACIÓN
# ==================================================

print("\nAnalizando audio...")

audio = AudioFileClip(audio_path)

duration = audio.duration

audio.close()

print(
    f"Duración detectada: "
    f"{duration:.2f} segundos"
)

# ==================================================
# CONVERSIÓN
# ==================================================

print("\nGenerando MP3...\n")

total_segments = len(segments)

for i, seg in enumerate(segments):

    start = seg["start"]

    if i < total_segments - 1:
        end = segments[i + 1]["start"]
    else:
        end = duration

    nombre = (
        sanitize_filename(
            seg["title"]
        ) + ".mp3"
    )

    destino = os.path.join(
        OUTPUT_DIR,
        nombre
    )

    audio_clip = None
    clip = None

    try:

        audio_clip = AudioFileClip(
            audio_path
        )

        clip = crear_subclip(
            audio_clip,
            start,
            end
        )

        guardar_audio(
            clip,
            destino
        )

    except Exception as e:

        print(
            f"\nERROR en '{nombre}':"
        )
        print(e)

        continue

    finally:

        try:
            if clip:
                clip.close()
        except:
            pass

        try:
            if audio_clip:
                audio_clip.close()
        except:
            pass

    porcentaje = (
        (i + 1)
        / total_segments
    ) * 100

    print(
        f"[{i + 1}/{total_segments}] "
        f"{porcentaje:6.2f}% -> "
        f"{nombre}"
    )

# ==================================================
# LIMPIEZA
# ==================================================

try:
    os.remove(audio_path)
    print("\nAudio temporal eliminado.")
except Exception:
    pass

print("\nProceso completado.")
print(f"Carpeta de salida:\n{OUTPUT_DIR}")
