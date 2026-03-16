"""Pure image-processing functions for overlay rendering and marker drawing."""
import cv2
import numpy as np
from logger_config import get_logger

logger = get_logger(__name__)


def draw_markers_on_frame(frame, markers, color=(0, 0, 255)):
    """Draw annotation markers on frame.
    
    Args:
        frame: BGR numpy array
        markers: List of marker dicts with x, y (relative 0-1), label, angle, length
        color: BGR tuple for marker color
    Returns:
        Modified frame
    """
    frame_h, frame_w = frame.shape[:2]

    for marker in markers:
        x = int(marker['x'] * frame_w)
        y = int(marker['y'] * frame_h)
        label = marker['label']
        angle = marker.get('angle', 45)
        arrow_length = marker.get('length', 30)

        angle_rad = np.radians(angle)
        end_x = int(x + arrow_length * np.cos(angle_rad))
        end_y = int(y + arrow_length * np.sin(angle_rad))

        cv2.line(frame, (x, y), (end_x, end_y), color, 2)
        cv2.circle(frame, (x, y), 4, color, -1)
        cv2.circle(frame, (end_x, end_y), 12, (255, 255, 255), -1)
        cv2.circle(frame, (end_x, end_y), 12, color, 2)

        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(label, font, 0.5, 2)[0]
        text_x = end_x - text_size[0] // 2
        text_y = end_y + text_size[1] // 2
        cv2.putText(frame, label, (text_x, text_y), font, 0.5, color, 2)

    return frame


def draw_reference_annotations(img, checkboxes, markers):
    """Draw checkboxes and markers on reference image.
    
    Args:
        img: BGR numpy array
        checkboxes: List of checkbox dicts with x, y (relative 0-1), checked
        markers: List of marker dicts
    Returns:
        Modified image
    """
    img_h, img_w = img.shape[:2]

    for cb in checkboxes:
        x = int(cb['x'] * img_w)
        y = int(cb['y'] * img_h)

        if cb['checked']:
            cv2.rectangle(img, (x - 16, y - 16), (x + 16, y + 16), (0, 193, 255), -1)
            cv2.rectangle(img, (x - 16, y - 16), (x + 16, y + 16), (0, 193, 255), 4)
            cv2.line(img, (x - 8, y), (x - 3, y + 8), (0, 0, 0), 4)
            cv2.line(img, (x - 3, y + 8), (x + 10, y - 8), (0, 0, 0), 4)
        else:
            cv2.rectangle(img, (x - 16, y - 16), (x + 16, y + 16), (255, 255, 255), -1)
            cv2.rectangle(img, (x - 16, y - 16), (x + 16, y + 16), (0, 193, 255), 3)

    for marker in markers:
        x = int(marker['x'] * img_w)
        y = int(marker['y'] * img_h)
        label = marker['label']
        angle = marker.get('angle', 45)
        arrow_length = marker.get('length', 30)

        angle_rad = np.radians(angle)
        end_x = int(x + arrow_length * np.cos(angle_rad))
        end_y = int(y + arrow_length * np.sin(angle_rad))

        cv2.line(img, (x, y), (end_x, end_y), (94, 194, 119), 2)
        cv2.circle(img, (x, y), 4, (94, 194, 119), -1)
        cv2.circle(img, (end_x, end_y), 12, (255, 255, 255), -1)
        cv2.circle(img, (end_x, end_y), 12, (94, 194, 119), 2)

        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(label, font, 0.5, 2)[0]
        text_x = end_x - text_size[0] // 2
        text_y = end_y + text_size[1] // 2
        cv2.putText(img, label, (text_x, text_y), font, 0.5, (94, 194, 119), 2)

    return img


def render_overlay_on_frame(frame, reference_image_path, has_alpha, overlay_scale,
                            overlay_x_offset, overlay_y_offset, overlay_rotation,
                            overlay_transparency, cache):
    """Render overlay on frame using transform settings.
    
    Args:
        frame: BGR numpy array
        reference_image_path: Path to overlay image
        has_alpha: Whether image has alpha channel
        overlay_scale: Scale percentage (50-200)
        overlay_x_offset: X offset in pixels
        overlay_y_offset: Y offset in pixels
        overlay_rotation: Rotation in degrees
        overlay_transparency: Transparency percentage (0-100)
        cache: Dict with keys 'params' and 'canvas' for caching transformed overlay.
               Will be mutated to store cache state.
    Returns:
        Blended frame, or original frame on failure
    """
    import os
    if not reference_image_path or not os.path.exists(reference_image_path):
        return frame

    try:
        h, w = frame.shape[:2]

        if has_alpha:
            scale = overlay_scale / 100.0
            cache_key = (reference_image_path, scale, overlay_x_offset, overlay_y_offset,
                         overlay_rotation, w, h)

            if cache.get('params') != cache_key:
                ref_img = cv2.imread(reference_image_path, cv2.IMREAD_UNCHANGED)

                if ref_img is not None and len(ref_img.shape) == 3 and ref_img.shape[2] == 4:
                    new_w = int(ref_img.shape[1] * scale)
                    new_h = int(ref_img.shape[0] * scale)

                    if new_w > 0 and new_h > 0:
                        ref_scaled = cv2.resize(ref_img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

                        if overlay_rotation != 0:
                            center = (new_w // 2, new_h // 2)
                            rot_matrix = cv2.getRotationMatrix2D(center, overlay_rotation, 1.0)
                            ref_scaled = cv2.warpAffine(ref_scaled, rot_matrix, (new_w, new_h),
                                                        borderMode=cv2.BORDER_CONSTANT,
                                                        borderValue=(0, 0, 0, 0))

                        canvas = np.zeros((h, w, 4), dtype=np.uint8)
                        x_pos = (w - new_w) // 2 + overlay_x_offset
                        y_pos = (h - new_h) // 2 + overlay_y_offset

                        x_start = max(0, x_pos)
                        y_start = max(0, y_pos)
                        x_end = min(w, x_pos + new_w)
                        y_end = min(h, y_pos + new_h)

                        src_x_start = max(0, -x_pos)
                        src_y_start = max(0, -y_pos)
                        src_x_end = src_x_start + (x_end - x_start)
                        src_y_end = src_y_start + (y_end - y_start)

                        if x_end > x_start and y_end > y_start:
                            canvas[y_start:y_end, x_start:x_end] = ref_scaled[src_y_start:src_y_end, src_x_start:src_x_end]

                        cache['canvas'] = canvas
                        cache['params'] = cache_key
                    else:
                        cache['canvas'] = None
                        cache['params'] = cache_key
                else:
                    cache['canvas'] = None
                    cache['params'] = cache_key

            if cache.get('canvas') is not None:
                overlay_bgr = cache['canvas'][:, :, :3]
                overlay_alpha = cache['canvas'][:, :, 3].astype(float) / 255.0
                overlay_alpha = overlay_alpha * (overlay_transparency / 100.0)
                alpha_3ch = np.stack([overlay_alpha] * 3, axis=2)

                blended = (overlay_bgr.astype(float) * alpha_3ch +
                           frame.astype(float) * (1 - alpha_3ch)).astype(np.uint8)
                return blended
        else:
            ref_img = cv2.imread(reference_image_path)
            if ref_img is not None:
                ref_resized = cv2.resize(ref_img, (w, h))
                alpha = overlay_transparency / 100.0
                blended = cv2.addWeighted(ref_resized, alpha, frame, 1 - alpha, 0)
                return blended
    except Exception as e:
        logger.error(f"Error rendering overlay: {e}")

    return frame
