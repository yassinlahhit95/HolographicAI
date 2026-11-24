# Etapa 4 - Webcam: detecta SI hay una persona delante y DONDE esta (aproximadamente).
#
# - NO identifica a nadie: solo busca "algo con forma de cara" (modelo YuNet de OpenCV).
# - NO guarda imagenes ni video: cada fotograma se analiza en memoria y se descarta.
# - Mientras la camara esta encendida, el holograma muestra "● CAMERA ON / CÁMARA ON"
#   (y se enciende la luz de la propia webcam).
#
# Prueba suelta (sin holograma):  Tools\tts\.venv\Scripts\python.exe Scripts\vision.py
import json
import math
import os
import re
import socket
import subprocess
import threading
import time

import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(ROOT, "Tools", "vision", "face_detection_yunet_2023mar.onnx")

# ------------------------------------------------------------------ ajustes
CAMERA_NAME = "HP Wide Vision"   # parte del nombre de la webcam a usar
CAMERA_INDEX = None              # o un numero fijo (0, 1, ...) si la busqueda por nombre falla
FLIP_X = False                   # True si el holograma mira al lado CONTRARIO de la persona
FPS = 12                         # analisis por segundo (suficiente y apenas usa procesador)
DETECT_W, DETECT_H = 640, 480    # tamano de analisis (640x480 = detecta hasta ~3 m; 320x240 = ~1,6 m)
MIN_SCORE = 0.75                 # confianza minima para aceptar una cara
APPEAR_FRAMES = 3                # fotogramas seguidos para decidir "hay alguien" (~0,25 s)
DISAPPEAR_SEC = 1.2              # segundos sin cara para decidir "se ha ido"
DARK_LEVEL = 25                  # brillo medio por debajo del cual avisamos de poca luz
FACE_WIDTH_M = 0.15              # ancho medio de una cara, para estimar la distancia
HFOV_DEG = 74.0                  # angulo horizontal aproximado de la HP Wide Vision


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def find_camera():
    """Indice de la webcam integrada. El orden de DirectShow es el que lista ffmpeg."""
    if CAMERA_INDEX is not None:
        return CAMERA_INDEX
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                             capture_output=True, text=True, errors="replace", timeout=15).stderr
        names = re.findall(r'"([^"]+)" \(video\)', out)
        for i, n in enumerate(names):
            if CAMERA_NAME.lower() in n.lower():
                return i
    except (OSError, subprocess.SubprocessError):
        pass
    return 0


class FaceTracker:
    """Hilo que lee la webcam y llama a on_update(present, x, y) unas 10 veces por segundo.
    x: -1 izquierda .. +1 derecha de la imagen de la camara; y: -1 arriba .. +1 abajo."""

    def __init__(self, on_update=None, on_camera=None, verbose=True):
        self.on_update = on_update or (lambda *a: None)
        self.on_camera = on_camera or (lambda on: None)
        self.verbose = verbose
        self.present = False
        self.x = self.y = 0.0
        self.distance = None
        self.brightness = None
        self.fps = 0.0
        self.error = None
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _run(self):
        cv2.setNumThreads(1)   # deja el procesador para Whisper y la IA
        idx = find_camera()
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            self.error = "no se pudo abrir la camara %d" % idx
            log("CAMARA: " + self.error + " (¿la usa otra aplicacion?). El holograma sigue sin camara.")
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        det = cv2.FaceDetectorYN.create(MODEL, "", (DETECT_W, DETECT_H), MIN_SCORE, 0.3, 5)
        focal = (DETECT_W / 2) / math.tan(math.radians(HFOV_DEG / 2))
        self.on_camera(True)
        if self.verbose:
            log("CAMARA ENCENDIDA (webcam %d). No se guarda ninguna imagen." % idx)

        seen, last_seen, last_send, last_dark_warn = 0, 0.0, 0.0, 0.0
        n_frames, t_fps = 0, time.time()
        try:
            while not self._stop.is_set():
                t0 = time.time()
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.2)
                    continue
                small = cv2.resize(frame, (DETECT_W, DETECT_H))
                del frame                                   # la imagen original se descarta ya
                self.brightness = float(small.mean())
                _, faces = det.detect(small)
                del small

                best = None
                if faces is not None and len(faces):
                    best = max(faces, key=lambda f: f[2] * f[3])   # la cara mas grande = la mas cercana
                now = time.time()
                if best is not None:
                    seen += 1
                    last_seen = now
                    # punto entre los ojos (landmarks 0 y 1): mejor objetivo para la mirada que el centro de la cara
                    ex = (best[4] + best[6]) / 2.0
                    ey = (best[5] + best[7]) / 2.0
                    x = ex / DETECT_W * 2.0 - 1.0
                    self.x = -x if FLIP_X else x
                    self.y = ey / DETECT_H * 2.0 - 1.0
                    self.distance = FACE_WIDTH_M * focal / max(best[2], 1.0)
                    if not self.present and seen >= APPEAR_FRAMES:
                        self.present = True
                        if self.verbose:
                            log("CAMARA: persona detectada (a ~%.1f m)" % self.distance)
                else:
                    seen = 0
                    if self.present and now - last_seen > DISAPPEAR_SEC:
                        self.present = False
                        if self.verbose:
                            log("CAMARA: ya no hay nadie")

                if self.brightness < DARK_LEVEL and now - last_dark_warn > 60 and self.verbose:
                    log("CAMARA: hay poca luz (brillo %.0f); la deteccion puede fallar" % self.brightness)
                    last_dark_warn = now

                if now - last_send >= 0.1:
                    self.on_update(self.present, self.x, self.y)
                    last_send = now

                n_frames += 1
                if now - t_fps >= 2.0:
                    self.fps, n_frames, t_fps = n_frames / (now - t_fps), 0, now
                time.sleep(max(0.0, 1.0 / FPS - (time.time() - t0)))
        finally:
            cap.release()
            self.present = False
            self.on_update(False, 0.0, 0.0)
            self.on_camera(False)
            if self.verbose:
                log("CAMARA APAGADA")


def unreal_sender(port=7810):
    """Funciones que envian el estado de la camara al holograma (UDP local)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(msg):
        sock.sendto(json.dumps(msg).encode("utf-8"), ("127.0.0.1", port))

    def on_update(present, x, y):
        send({"cmd": "face", "present": bool(present), "x": round(float(x), 3), "y": round(float(y), 3)})

    def on_camera(on):
        send({"cmd": "camera", "on": bool(on)})

    return on_update, on_camera


if __name__ == "__main__":
    # Prueba: muestra lo que detecta durante 30 s y tambien mueve el holograma si esta abierto.
    up, cam = unreal_sender()
    t = FaceTracker(up, cam).start()
    try:
        for _ in range(60):
            time.sleep(0.5)
            if t.error:
                break
            print("   presente=%-5s x=%+.2f y=%+.2f distancia=%s brillo=%s fps=%.1f" % (
                t.present, t.x, t.y, "%.1f m" % t.distance if t.distance else "-",
                "%.0f" % t.brightness if t.brightness is not None else "-", t.fps), flush=True)
    except KeyboardInterrupt:
        pass
    t.stop()
