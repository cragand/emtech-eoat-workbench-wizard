"""Template workflow manager — syncs git-tracked templates to user working directories."""
import hashlib
import json
import os
import shutil
from logger_config import get_logger

logger = get_logger(__name__)

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MANIFEST_PATH = os.path.join(_APP_DIR, "settings", "template_hashes.json")


def _hash_file(path):
    """Return SHA-256 hex digest of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest():
    if os.path.exists(_MANIFEST_PATH):
        try:
            with open(_MANIFEST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.warning("Failed to load template manifest, starting fresh", exc_info=True)
    return {}


def _save_manifest(manifest):
    os.makedirs(os.path.dirname(_MANIFEST_PATH), exist_ok=True)
    tmp = _MANIFEST_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    os.replace(tmp, _MANIFEST_PATH)


def _copy_template(template_path, dest_dir, templates_res_dir):
    """Copy a template JSON to dest_dir, copying any referenced resources."""
    with open(template_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)

    for step in workflow.get("steps", []):
        for key in ("reference_image", "reference_video"):
            ref = step.get(key, "")
            if not ref:
                continue
            # Resolve relative to templates dir
            abs_ref = os.path.normpath(os.path.join(os.path.dirname(template_path), ref))
            if os.path.exists(abs_ref):
                dest_res = os.path.join(dest_dir, os.path.basename(abs_ref))
                if not os.path.exists(dest_res):
                    shutil.copy2(abs_ref, dest_res)
                step[key] = os.path.basename(abs_ref)

    dest_path = os.path.join(dest_dir, os.path.basename(template_path))
    tmp = dest_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(workflow, f, indent=2)
    os.replace(tmp, dest_path)
    return dest_path


def sync_templates(parent_widget=None):
    """Scan template directories and sync new/updated templates to working dirs.

    Called once on startup.  Returns list of messages for logging.
    """
    from PyQt5.QtWidgets import QMessageBox

    manifest = _load_manifest()
    updated = False
    messages = []

    workflow_dirs = [
        ("qc_workflows", os.path.join(_APP_DIR, "workflows", "qc_workflows")),
        ("maintenance_workflows", os.path.join(_APP_DIR, "workflows", "maintenance_workflows")),
    ]

    for category, work_dir in workflow_dirs:
        templates_dir = os.path.join(work_dir, "templates")
        templates_res_dir = os.path.join(templates_dir, "resources")
        if not os.path.isdir(templates_dir):
            continue

        for fname in os.listdir(templates_dir):
            if not fname.endswith(".json"):
                continue

            template_path = os.path.join(templates_dir, fname)
            manifest_key = f"{category}/{fname}"
            current_hash = _hash_file(template_path)
            prev_hash = manifest.get(manifest_key)
            dest_path = os.path.join(work_dir, fname)

            if prev_hash is None and not os.path.exists(dest_path):
                # New template, no local copy — auto-install
                _copy_template(template_path, work_dir, templates_res_dir)
                manifest[manifest_key] = current_hash
                updated = True
                messages.append(f"Installed new template: {fname}")
                logger.info("Installed new template: %s/%s", category, fname)

            elif prev_hash is None and os.path.exists(dest_path):
                # First run with template system, user already has a copy — seed manifest
                manifest[manifest_key] = current_hash
                updated = True

            elif current_hash != prev_hash:
                # Template updated upstream
                if not os.path.exists(dest_path):
                    # User deleted their copy — just install fresh
                    _copy_template(template_path, work_dir, templates_res_dir)
                    manifest[manifest_key] = current_hash
                    updated = True
                    messages.append(f"Installed updated template: {fname}")
                    logger.info("Installed updated template (no local copy): %s/%s", category, fname)
                elif parent_widget:
                    # User has a local copy — ask before overwriting
                    try:
                        with open(template_path, "r", encoding="utf-8") as f:
                            tpl_name = json.load(f).get("name", fname)
                    except Exception:
                        tpl_name = fname

                    reply = QMessageBox.question(
                        parent_widget,
                        "Template Update Available",
                        f"The template \"{tpl_name}\" has been updated.\n\n"
                        f"Would you like to update your local copy?\n"
                        f"Your current version will be backed up.",
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    if reply == QMessageBox.Yes:
                        # Backup existing
                        backup = dest_path.replace(".json", "_backup.json")
                        n = 1
                        while os.path.exists(backup):
                            backup = dest_path.replace(".json", f"_backup_{n}.json")
                            n += 1
                        shutil.copy2(dest_path, backup)
                        _copy_template(template_path, work_dir, templates_res_dir)
                        messages.append(f"Updated template: {fname} (backup: {os.path.basename(backup)})")
                        logger.info("Updated template %s/%s, backup at %s", category, fname, backup)

                    # Update manifest either way so we don't ask again
                    manifest[manifest_key] = current_hash
                    updated = True
                else:
                    # No parent widget (headless) — just update manifest
                    manifest[manifest_key] = current_hash
                    updated = True

    if updated:
        _save_manifest(manifest)

    return messages
