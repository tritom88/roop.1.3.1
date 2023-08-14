from typing import Any, List
import cv2
import threading
import gfpgan

import roop.globals
import roop.processors.frame.core
from roop.core import update_status
from roop.face_analyser import get_one_face
from roop.utilities import conditional_download, resolve_relative_path, is_image, is_video
from PIL import Image
from numpy import asarray

FACE_ENHANCER = None
THREAD_SEMAPHORE = threading.Semaphore()
THREAD_LOCK = threading.Lock()
NAME = 'ROOP.FACE-ENHANCER'


def pre_check() -> bool:
    download_directory_path = resolve_relative_path('../models')
    conditional_download(download_directory_path, ['https://huggingface.co/henryruhs/roop/resolve/main/GFPGANv1.3.pth'])
    return True


def pre_start() -> bool:
    if not is_image(roop.globals.target_path) and not is_video(roop.globals.target_path):
        update_status('Select an image or video for target path.', NAME)
        return False
    return True


def get_face_enhancer() -> None:
    global FACE_ENHANCER

    with THREAD_LOCK:
        if FACE_ENHANCER is None:
            model_path = resolve_relative_path('../models/GFPGANv1.3.pth')
            # todo: set models path https://github.com/TencentARC/GFPGAN/issues/399
            FACE_ENHANCER = gfpgan.GFPGANer(model_path=model_path, upscale=1)
    return FACE_ENHANCER


def enhance_face(temp_frame: Any) -> Any:
    with THREAD_SEMAPHORE:
        temp_frame_original = Image.fromarray(temp_frame)
        _, _, temp_frame = get_face_enhancer().enhance(
            temp_frame,
            paste_back=True
        )            
        temp_frame = Image.blend(temp_frame_original, Image.fromarray(temp_frame), 0.75)         
    return asarray(temp_frame)


def process_frame(source_face: Any, temp_frame: Any) -> Any:
    target_face = get_one_face(temp_frame)
    if target_face:
        temp_frame = enhance_face(temp_frame)
    return temp_frame


def process_frames(source_path: str, temp_frame_paths: List[str], progress=None) -> None:
    for temp_frame_path in temp_frame_paths:
        temp_frame = cv2.imread(temp_frame_path)
        result = process_frame(None, temp_frame)
        cv2.imwrite(temp_frame_path, result)
        if progress:
            progress.update(1)


def process_image(source_path: str, target_path: str, output_path: str) -> None:
    target_frame = cv2.imread(target_path)
    result = process_frame(None, target_frame)
    cv2.imwrite(output_path, result)


def process_video(source_path: str, temp_frame_paths: List[str]) -> None:
    roop.processors.frame.core.process_video(None, temp_frame_paths, process_frames)
