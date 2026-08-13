#!/usr/bin/env python3
"""Vendor-neutral, fail-closed runner for source-faithful image workflows.

Adapters are explicit local executables. They receive one JSON object on stdin
and must return one JSON object on stdout. This runner contains no service URL,
model selection, SDK, or credential handling. Adapters inherit the caller's
environment and remain responsible for transport and authentication.

The two phases form a self-contained creative and execution workflow:

1. ``inspect`` verifies pixel inspection and writes a fingerprinted state file.
2. ``generate`` builds an Asset Board, routes a Y2K style, compiles the final
   prompt, verifies reference-image generation, dispatches generation, performs
   a pixel-grounded output quality check, and applies at most one correction.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


RUNNER_CONTRACT = "source-faithful-image-runner/v1"
INSPECTION_CONTRACT = "image-inspection-provider/v1"
GENERATION_CONTRACT = "image-generation-provider/v1"

PIXEL_INSPECTION_FAILURE = (
    "I cannot inspect the actual pixels of the supplied images in this "
    "environment, so I cannot create a source-faithful poster. Please switch "
    "to a vision-capable model or configure an image-inspection Provider, "
    "then run the workflow again."
)
REFERENCE_GENERATION_FAILURE = (
    "The available image generator is text-to-image only and cannot use the "
    "supplied photos as visual references. I cannot preserve the subjects "
    "faithfully with this backend. Please use a reference-image-capable "
    "generation or editing model, then run the workflow again."
)

SOURCE_ANALYSIS_SCOPE = [
    "pixel_dimensions",
    "visible_subjects_and_objects",
    "identity_preserving_visual_attributes",
    "visible_positions_and_interactions",
    "pose_gaze_gesture_and_direction",
    "extractable_units_and_crop_opportunities",
    "composition_color_lighting_and_negative_space",
    "future_cues_and_spatial_affordances",
    "focus_noise_compression_exposure_occlusion_and_usable_detail",
]

OUTPUT_ANALYSIS_SCOPE = [
    "identity_and_object_fidelity",
    "face_body_outfit_and_prop_associations",
    "text_accuracy",
    "edge_quality_and_anatomy",
    "source_crop_recognizability",
    "palette_texture_and_material_consistency",
    "hero_hierarchy_and_eye_path",
    "thumbnail_readability",
    "style_coherence_and_density",
]

INSPECTION_LIST_FIELDS = [
    "visible_subjects",
    "visible_objects",
    "identity_attributes",
    "visible_positions_and_interactions",
    "extractable_units",
    "crop_opportunities",
    "composition",
    "future_cues",
    "spatial_affordances",
    "image_condition",
    "uncertainties",
]

SOURCE_TYPES = {"path", "uri", "file_id", "image_handle"}
IMAGE_LOCATOR_TYPES = SOURCE_TYPES | {"base64"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
RATIO_PATTERN = re.compile(r"^([1-9][0-9]{0,4}):([1-9][0-9]{0,4})$")
FORMAT_PATTERN = re.compile(r"^[A-Za-z0-9._+-]{2,32}$")

GENERIC_INSPECTION_PHRASES = {
    "image received",
    "image received successfully",
    "the image contains a person",
    "the image contains an object",
    "unable to determine",
}

STYLE_ORDER = [
    "pop_scrapbook",
    "webcore_desktop",
    "punk_halftone",
    "liquid_chrome_futurism",
    "techno_pop_campaign",
]

STYLE_FAMILIES: Dict[str, Dict[str, Any]] = {
    "pop_scrapbook": {
        "label": "Pop Scrapbook",
        "cues": [
            "group", "fashion", "full body", "full-body", "performance", "pose", "colorful",
            "saturated", "collectible", "playful", "outfit", "friends", "stage",
            "合照", "时尚", "全身", "表演", "姿势", "鲜艳", "服装", "舞台",
        ],
        "composition": (
            "Use one dominant clean source cutout, a small number of portrait or detail cards, "
            "diagonal overlap, outlined display type when text is supplied, and generous gaps "
            "between dense clusters."
        ),
        "transformations": ["clean cutout", "monochrome portrait card", "halftone echo", "accessory close-up"],
        "palette": "saturated blue and hot pink with black, white, and one quiet paper neutral",
        "type": "outlined display lettering with rounded label capsules and a compact condensed sans",
        "preferred_stages": ["flat editorial field"],
        "preferred_materials": ["paper, ink, toner, tape, and fibrous edges", "translucent sticker plastic"],
        "avoid": "equal-size portrait grids, identical outlines around every face, and generic fan merchandise",
    },
    "webcore_desktop": {
        "label": "Webcore Desktop",
        "cues": [
            "selfie", "screen", "camera", "phone", "computer", "monitor", "device", "interface",
            "diary", "cursor", "player", "webcam", "digital", "pixel", "casual snapshot",
            "自拍", "屏幕", "相机", "手机", "电脑", "设备", "界面", "数码", "像素",
        ],
        "composition": (
            "Place the fidelity hero inside or crossing one chunky window, add one nested camera or player replay, "
            "a cursor path, and a controlled stack of low-resolution status panels."
        ),
        "transformations": ["pixelated thumbnail", "low-resolution replay", "scan crop", "selection box"],
        "palette": "turn-of-the-millennium desktop blue, cool grey, white, cyan, and one warning accent",
        "type": "bitmap labels, compact system copy, and restrained pixel sans typography",
        "preferred_stages": ["desktop or interface space"],
        "preferred_materials": ["CRT glow, pixels, scan lines, compression, and translucent screen overlays"],
        "avoid": "contemporary glass-interface styling, polished dashboard layouts, and exact branded software replicas",
    },
    "punk_halftone": {
        "label": "Punk Halftone",
        "cues": [
            "dark", "black", "contrast", "performance", "confrontational", "expressive", "grain",
            "print", "poster", "stage", "rough", "shadow", "monochrome", "close-up",
            "暗色", "黑色", "高对比", "表演", "颗粒", "印刷", "海报", "粗糙", "阴影", "单色", "特写",
        ],
        "composition": (
            "Use an overscale monochrome face or body fragment, hard rectangular crops, one sharp diagonal, "
            "and a dense type block balanced by a quieter black or paper field."
        ),
        "transformations": ["duotone", "coarse halftone", "xerox contrast", "registration shift", "torn cutout"],
        "palette": "black and off-white with electric blue or dirty red as the single aggressive accent",
        "type": "condensed grotesk with one rough serif, stamped mono, or cut-and-paste accent",
        "preferred_stages": ["flat editorial field"],
        "preferred_materials": ["paper, ink, toner, tape, and fibrous edges"],
        "avoid": "uniform distress, unreadable pseudo-copy, horror mutilation, and accidental heavy-metal pastiche",
    },
    "liquid_chrome_futurism": {
        "label": "Liquid Chrome Futurism",
        "cues": [
            "reflective", "jewelry", "metal", "chrome", "glass", "fluid", "sleek", "curved", "beauty",
            "water", "iridescent", "silver", "mirror", "gloss", "accessory", "synthetic",
            "反光", "首饰", "金属", "铬", "玻璃", "流动", "光滑", "曲线", "水", "银色", "镜面",
        ],
        "composition": (
            "Keep one clear fidelity hero and interrupt it with a single biomorphic reflective portal, ribbon, "
            "or liquid frame; use reflections or insets as echoes instead of arbitrary duplicates."
        ),
        "transformations": ["mirror-edged cutout", "chrome contour", "warped reflective replay", "iridescent crop"],
        "palette": "silver, graphite, icy cyan, electric blue, violet shadow, and one hot signal accent",
        "type": "stretched techno sans or narrow extended grotesk with one restrained reflective accent",
        "preferred_stages": ["product or industrial void", "cosmic or atmospheric zone", "synthetic laboratory"],
        "preferred_materials": ["liquid chrome, mirror metal, iridescent film, and high-specular droplets"],
        "avoid": "random three-dimensional blobs, luxury-logo styling, inconsistent reflections, and covered identity anchors",
    },
    "techno_pop_campaign": {
        "label": "Techno Pop Campaign",
        "cues": [
            "promotional portrait", "campaign", "consumer tech", "consumer-tech", "gadget", "device",
            "console", "controller", "handheld", "laptop", "computer", "camera", "speaker", "screen",
            "product", "game cover", "game-cover", "toy", "plastic", "acrylic", "hard flash",
            "full body", "full-body", "fashion", "pose", "advertisement", "catalog",
            "宣传肖像", "广告", "消费电子", "科技产品", "设备", "掌机", "游戏机", "控制器",
            "笔记本电脑", "电脑", "相机", "扬声器", "屏幕", "产品", "游戏封面", "玩具",
            "塑料", "亚克力", "硬闪光", "全身", "时尚", "姿势",
        ],
        "composition": (
            "Build one coherent product world around a clear promotional hero. Turn one oversized, "
            "source-responsive gadget, product shell, screen, control surface, aquarium, speaker, camera, "
            "console, or synthetic display into architecture. Let the hero sit on, lean against, emerge from, "
            "overlap, or appear inside that device. Add one to three smaller promotional replays only when they "
            "clarify pose, clothing, scale, or campaign narrative; never reduce the hardware to detached stickers."
        ),
        "transformations": [
            "high-contrast promotional hero",
            "hard-flash portrait",
            "slightly overexposed highlight treatment",
            "saturated beauty crop",
            "product-screen replay",
            "catalog-scale cutout",
            "early-digital advertisement echo",
        ],
        "palette": (
            "one dominant saturated campaign color, one strong contrasting dark, and white, silver, grey, "
            "or transparent plastic as engineered neutrals, with minor source-derived accents"
        ),
        "type": (
            "one short game-cover or product-mark title using wide, italic, inflated, outlined, beveled, "
            "winged, star-framed, or speed-line display lettering"
        ),
        "preferred_stages": ["product or industrial void", "desktop or interface space"],
        "preferred_materials": [
            "brushed metal, molded shells, vents, cables, ports, and engineered seams",
            "glass, acrylic, clear housings, fiber optics, bubbles, and luminous edges",
        ],
        "directives": (
            "Treat the hero as early-digital commercial glamour: heighten facial and hair contrast, keep crisp "
            "dark features, slightly enrich natural skin, lip, cheek, makeup, and clothing color, and permit "
            "controlled hard-flash bloom with mildly blown highlights on flash-facing planes. Preserve facial "
            "geometry and some natural skin texture. Keep the hero clearest; confine stronger halftone, color "
            "bleed, compression, and edge glow to smaller replays. The portrait must be visibly processed but "
            "never illustrated, doll-like, plastic, melted, excessively smoothed, or replaced by a new face. "
            "Make the oversized device a spatial stage with physically readable interaction, not decoration."
        ),
        "avoid": (
            "an untouched natural portrait pasted onto a background, generic beauty retouching, excessive skin "
            "smoothing, highlight clipping that erases facial features, identity-changing saturation, unrelated "
            "gadget stickers, a flat product catalog, contemporary luxury advertising, clean modern interfaces, "
            "copied game or music logos, and devices or titles that overpower the recognizable hero"
        ),
    },
}

STYLE_ALIASES = {
    "auto": "auto",
    "pop": "pop_scrapbook",
    "pop scrapbook": "pop_scrapbook",
    "pop_scrapbook": "pop_scrapbook",
    "webcore": "webcore_desktop",
    "webcore desktop": "webcore_desktop",
    "webcore_desktop": "webcore_desktop",
    "punk": "punk_halftone",
    "punk halftone": "punk_halftone",
    "punk_halftone": "punk_halftone",
    "liquid chrome": "liquid_chrome_futurism",
    "liquid chrome futurism": "liquid_chrome_futurism",
    "liquid_chrome_futurism": "liquid_chrome_futurism",
    "techno pop": "techno_pop_campaign",
    "techno pop campaign": "techno_pop_campaign",
    "techno_pop_campaign": "techno_pop_campaign",
    "tech pop campaign": "techno_pop_campaign",
    "consumer tech campaign": "techno_pop_campaign",
    "gadget world": "techno_pop_campaign",
    "game cover": "techno_pop_campaign",
    "流行剪贴簿": "pop_scrapbook",
    "流行拼贴": "pop_scrapbook",
    "网页桌面": "webcore_desktop",
    "复古桌面": "webcore_desktop",
    "朋克网点": "punk_halftone",
    "朋克半调": "punk_halftone",
    "液态铬": "liquid_chrome_futurism",
    "液态铬未来主义": "liquid_chrome_futurism",
    "科技流行广告": "techno_pop_campaign",
    "科技产品广告": "techno_pop_campaign",
    "消费电子广告": "techno_pop_campaign",
    "产品科技广告": "techno_pop_campaign",
    "游戏封面": "techno_pop_campaign",
}

# A supporting family may contribute exactly one bounded subsystem. Pair-specific
# rules prevent two families from competing for the whole world, palette,
# portrait treatment, typography, and material language.
SUPPORTING_PAIR_RULES: Dict[Tuple[str, str], Dict[str, str]] = {
    ("pop_scrapbook", "webcore_desktop"): {
        "subsystem": "one contained camera or player replay",
        "purpose": "interface support",
    },
    ("pop_scrapbook", "liquid_chrome_futurism"): {
        "subsystem": "one restrained chrome frame or hardware accent",
        "purpose": "material support",
    },
    ("pop_scrapbook", "techno_pop_campaign"): {
        "subsystem": "one oversized product-stage element and one restrained game-cover title",
        "purpose": "campaign support",
    },
    ("webcore_desktop", "pop_scrapbook"): {
        "subsystem": "one small editorial card or playful label layer",
        "purpose": "editorial support",
    },
    ("webcore_desktop", "punk_halftone"): {
        "subsystem": "print texture limited to thumbnails or status panels",
        "purpose": "print support",
    },
    ("punk_halftone", "webcore_desktop"): {
        "subsystem": "one contained low-resolution diagnostic or player window",
        "purpose": "interface support",
    },
    ("punk_halftone", "liquid_chrome_futurism"): {
        "subsystem": "one restrained chrome title or hardware accent",
        "purpose": "material support",
    },
    ("liquid_chrome_futurism", "pop_scrapbook"): {
        "subsystem": "one small editorial label-and-card subsystem",
        "purpose": "editorial support",
    },
    ("liquid_chrome_futurism", "punk_halftone"): {
        "subsystem": "halftone or xerox reproduction limited to the background and small echoes",
        "purpose": "print support",
    },
    ("techno_pop_campaign", "webcore_desktop"): {
        "subsystem": "one screen replay or compact control panel inside the oversized device",
        "purpose": "product-interface support",
    },
    ("techno_pop_campaign", "pop_scrapbook"): {
        "subsystem": "one small editorial card or playful label layer",
        "purpose": "editorial support",
    },
    ("techno_pop_campaign", "punk_halftone"): {
        "subsystem": "restrained print texture confined to small replays and reproduction artifacts",
        "purpose": "print support",
    },
    ("techno_pop_campaign", "liquid_chrome_futurism"): {
        "subsystem": "one restrained reflective title or hardware accent",
        "purpose": "material support",
    },
}

STAGE_CUES: Dict[str, List[str]] = {
    "flat editorial field": ["fashion", "group", "pose", "poster", "paper", "performance", "colorful", "时尚", "合照", "姿势", "海报", "纸张", "表演", "鲜艳"],
    "desktop or interface space": ["screen", "camera", "phone", "computer", "device", "digital", "interface", "屏幕", "相机", "手机", "电脑", "设备", "数码", "界面"],
    "nocturnal city or transit space": ["city", "street", "rail", "station", "platform", "tunnel", "road", "night", "城市", "街道", "轨道", "车站", "站台", "隧道", "道路", "夜晚"],
    "synthetic laboratory": ["scan", "laboratory", "medical", "diagnostic", "specimen", "technical", "white room", "扫描", "实验室", "诊断", "标本", "技术"],
    "product or industrial void": [
        "product", "metal", "machine", "vehicle", "industrial", "engineered", "object", "gadget",
        "console", "controller", "handheld", "laptop", "speaker", "product shell", "campaign",
        "产品", "金属", "机器", "车辆", "工业", "物体", "设备", "掌机", "游戏机", "控制器",
        "笔记本电脑", "扬声器", "产品外壳", "广告",
    ],
    "cosmic or atmospheric zone": ["sky", "cloud", "light", "haze", "space", "star", "atmosphere", "天空", "云", "光", "雾", "太空", "星", "大气"],
    "bio-tech habitat": ["plant", "water", "flora", "organic", "garden", "membrane", "aquatic", "植物", "水", "有机", "花园", "薄膜", "水生"],
}

MATERIAL_CUES: Dict[str, List[str]] = {
    "paper, ink, toner, tape, and fibrous edges": ["paper", "grain", "rough", "print", "dark", "poster", "fabric", "纸张", "颗粒", "粗糙", "印刷", "暗色", "海报", "织物"],
    "CRT glow, pixels, scan lines, compression, and translucent screen overlays": [
        "screen", "camera", "phone", "computer", "digital", "pixel", "device", "interface",
        "屏幕", "相机", "手机", "电脑", "数码", "像素", "设备", "界面"
    ],
    "liquid chrome, mirror metal, iridescent film, and high-specular droplets": [
        "reflective", "jewelry", "metal", "chrome", "silver", "mirror", "fluid", "sleek",
        "反光", "首饰", "金属", "铬", "银色", "镜面", "流动", "光滑"
    ],
    "glass, acrylic, clear housings, fiber optics, bubbles, and luminous edges": [
        "glass", "transparent", "clear", "bubble", "light", "lens", "玻璃", "透明", "气泡", "光", "镜头"
    ],
    "inflated plastic, jelly, silicone, vinyl, and soft translucent membranes": [
        "soft", "plastic", "toy", "rounded", "inflated", "colorful", "柔软", "塑料", "玩具", "圆润", "充气", "鲜艳"
    ],
    "wet reflective surfaces, mist, flare, and emissive atmospheric light": [
        "water", "wet", "road", "night", "mist", "rain", "glow", "水", "潮湿", "道路", "夜晚", "雾", "雨", "发光"
    ],
    "brushed metal, molded shells, vents, cables, ports, and engineered seams": [
        "machine", "vehicle", "industrial", "cable", "metal", "engineered", "device", "gadget",
        "console", "controller", "handheld", "laptop", "product shell", "molded plastic", "port",
        "机器", "车辆", "工业", "电缆", "金属", "工程", "设备", "掌机", "游戏机", "控制器",
        "笔记本电脑", "产品外壳", "模制塑料", "端口"
    ],
}

POOR_QUALITY_CUES = [
    "motion blur", "defocus", "out of focus", "jpeg blocking", "compression artifact",
    "destructive noise", "upscaling artifact", "clipped exposure", "insufficient detail",
    "severe blur", "badly exposed", "unusable", "heavy occlusion",
    "运动模糊", "失焦", "压缩伪影", "噪点严重", "曝光过度", "细节不足", "严重遮挡", "不可用",
]

CLEAR_QUALITY_CUES = [
    "sharp", "clear", "usable focus", "in focus", "well exposed", "good detail", "unobscured",
    "清晰", "对焦准确", "曝光良好", "细节良好", "无遮挡",
]


class RunnerError(Exception):
    """Structured runner failure safe for machine handling."""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require(condition: bool, code: str, message: str, **details: Any) -> None:
    if not condition:
        raise RunnerError(code, message, details)


def load_json(path: Path) -> Dict[str, Any]:
    require(path.is_file(), "missing_json_file", "Required JSON file was not found.", path=str(path))
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RunnerError(
            "invalid_json_file",
            "Could not read a valid UTF-8 JSON object.",
            {"path": str(path), "error_type": type(exc).__name__},
        )
    require(isinstance(value, dict), "invalid_json_root", "JSON root must be an object.", path=str(path))
    return value


def write_json_atomic(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = None
    temporary_name = None
    try:
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        )
        temporary_name = handle.name
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(temporary_name, path)
    except OSError as exc:
        if handle is not None and not handle.closed:
            handle.close()
        if temporary_name:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
        raise RunnerError(
            "json_write_failed",
            "Could not write the requested JSON file.",
            {"path": str(path), "error_type": type(exc).__name__},
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise RunnerError(
            "image_read_failed",
            "Could not read a source image.",
            {"path": str(path), "error_type": type(exc).__name__},
        )
    return digest.hexdigest()


def fingerprint_source(source_type: str, source: str) -> Dict[str, Any]:
    if source_type == "path":
        path = Path(source).expanduser().resolve()
        require(path.is_file(), "missing_source_image", "A source image path is not a file.", path=str(path))
        stat = path.stat()
        require(stat.st_size > 0, "empty_source_image", "A source image file is empty.", path=str(path))
        return {
            "source": str(path),
            "source_type": "path",
            "byte_size": stat.st_size,
            "sha256": sha256_file(path),
        }

    handle_digest = hashlib.sha256(f"{source_type}:{source}".encode("utf-8")).hexdigest()
    return {
        "source": source,
        "source_type": source_type,
        "handle_sha256": handle_digest,
    }


def normalize_source_images(request: Dict[str, Any]) -> List[Dict[str, Any]]:
    require(
        request.get("contract") == RUNNER_CONTRACT,
        "invalid_runner_contract",
        f"Request contract must be {RUNNER_CONTRACT}.",
    )
    raw_images = request.get("images")
    require(isinstance(raw_images, list) and raw_images, "missing_images", "Request must contain at least one image.")

    images: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    for index, raw in enumerate(raw_images):
        require(isinstance(raw, dict), "invalid_image_entry", "Each image entry must be an object.", index=index)
        image_id = raw.get("id")
        source = raw.get("source")
        source_type = raw.get("source_type")
        require(
            isinstance(image_id, str) and ID_PATTERN.fullmatch(image_id) is not None,
            "invalid_image_id",
            "Image id must use letters, digits, dots, underscores, or hyphens.",
            index=index,
        )
        require(image_id not in seen_ids, "duplicate_image_id", "Image ids must be unique.", image_id=image_id)
        require(
            isinstance(source, str) and source.strip(),
            "invalid_image_source",
            "Image source must be a non-empty string.",
            image_id=image_id,
        )
        require(source_type in SOURCE_TYPES, "invalid_source_type", "Unsupported image source type.", image_id=image_id)
        require(
            isinstance(raw.get("must_use", True), bool),
            "invalid_must_use",
            "must_use must be boolean.",
            image_id=image_id,
        )

        fingerprint = fingerprint_source(source_type, source.strip())
        images.append(
            {
                "id": image_id,
                "source": fingerprint["source"],
                "source_type": source_type,
                "must_use": raw.get("must_use", True),
                "fingerprint": fingerprint,
            }
        )
        seen_ids.add(image_id)

    return images


def resolve_executable(executable: str) -> str:
    candidate = Path(executable).expanduser()
    if candidate.parent != Path(".") or os.sep in executable:
        resolved = candidate.resolve()
        require(resolved.is_file(), "missing_adapter", "Adapter executable was not found.", adapter=str(resolved))
        require(
            os.access(str(resolved), os.X_OK),
            "adapter_not_executable",
            "Adapter file is not executable.",
            adapter=str(resolved),
        )
        return str(resolved)

    located = shutil.which(executable)
    require(located is not None, "missing_adapter", "Adapter executable was not found on PATH.", adapter=executable)
    return located


def invoke_adapter(
    executable: str,
    adapter_args: Sequence[str],
    payload: Dict[str, Any],
    timeout_seconds: int,
) -> Dict[str, Any]:
    command = [resolve_executable(executable)] + list(adapter_args)
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        raise RunnerError(
            "adapter_timeout",
            "Adapter did not finish within the configured timeout.",
            {"timeout_seconds": timeout_seconds},
        )
    except OSError as exc:
        raise RunnerError(
            "adapter_start_failed",
            "Adapter process could not be started.",
            {"error_type": type(exc).__name__},
        )

    require(
        completed.returncode == 0,
        "adapter_failed",
        "Adapter returned a non-zero exit status. Its stderr was withheld to avoid leaking secrets.",
        exit_status=completed.returncode,
    )
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise RunnerError(
            "invalid_adapter_response",
            "Adapter stdout must contain exactly one valid JSON object.",
        )
    require(isinstance(response, dict), "invalid_adapter_response", "Adapter response root must be an object.")
    return response


def request_capabilities(
    executable: str,
    adapter_args: Sequence[str],
    contract: str,
    timeout_seconds: int,
) -> Dict[str, Any]:
    response = invoke_adapter(
        executable,
        adapter_args,
        {"contract": contract, "operation": "capabilities"},
        timeout_seconds,
    )
    require(response.get("contract") == contract, "wrong_adapter_contract", "Adapter returned the wrong contract.")
    capabilities = response.get("capabilities")
    require(isinstance(capabilities, dict), "missing_capabilities", "Adapter did not return a capabilities object.")
    return capabilities


def list_of_strings(value: Any, field: str, allow_empty: bool = True) -> List[str]:
    require(isinstance(value, list), "invalid_inspection_field", "Inspection field must be a list.", field=field)
    cleaned: List[str] = []
    for item in value:
        require(
            isinstance(item, str),
            "invalid_inspection_field",
            "Inspection list items must be strings.",
            field=field,
        )
        text = item.strip()
        if text:
            cleaned.append(text)
    require(
        allow_empty or bool(cleaned),
        "empty_inspection_field",
        "Inspection field must not be empty.",
        field=field,
    )
    return cleaned


def validate_source_inspection_results(
    response: Dict[str, Any],
    images: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    require(response.get("contract") == INSPECTION_CONTRACT, "wrong_inspection_contract", PIXEL_INSPECTION_FAILURE)
    raw_results = response.get("results")
    require(isinstance(raw_results, list), "missing_inspection_results", PIXEL_INSPECTION_FAILURE)

    expected_by_id = {image["id"]: image for image in images}
    expected_ids = set(expected_by_id)
    by_id: Dict[str, Dict[str, Any]] = {}
    for raw in raw_results:
        require(isinstance(raw, dict), "invalid_inspection_result", PIXEL_INSPECTION_FAILURE)
        result_id = raw.get("id")
        require(result_id in expected_ids, "unknown_inspection_result", PIXEL_INSPECTION_FAILURE)
        require(result_id not in by_id, "duplicate_inspection_result", PIXEL_INSPECTION_FAILURE)
        require(
            raw.get("source") == expected_by_id[result_id]["source"],
            "inspection_source_mismatch",
            PIXEL_INSPECTION_FAILURE,
            image_id=result_id,
        )

        dimensions = raw.get("pixel_dimensions")
        require(
            isinstance(dimensions, dict),
            "missing_pixel_dimensions",
            PIXEL_INSPECTION_FAILURE,
            image_id=result_id,
        )
        width = dimensions.get("width")
        height = dimensions.get("height")
        require(
            isinstance(width, int) and width > 0 and isinstance(height, int) and height > 0,
            "invalid_pixel_dimensions",
            PIXEL_INSPECTION_FAILURE,
            image_id=result_id,
        )

        cleaned: Dict[str, Any] = {
            "id": result_id,
            "source": raw.get("source"),
            "pixel_dimensions": {"width": width, "height": height},
        }
        for field in INSPECTION_LIST_FIELDS:
            cleaned[field] = list_of_strings(raw.get(field), field, allow_empty=True)

        require(
            bool(cleaned["visible_subjects"] or cleaned["visible_objects"]),
            "ungrounded_inspection",
            PIXEL_INSPECTION_FAILURE,
            image_id=result_id,
        )
        require(
            bool(cleaned["composition"]),
            "missing_composition_analysis",
            PIXEL_INSPECTION_FAILURE,
            image_id=result_id,
        )
        require(
            bool(cleaned["image_condition"]),
            "missing_condition_analysis",
            PIXEL_INSPECTION_FAILURE,
            image_id=result_id,
        )

        evidence = " ".join(
            item
            for field in INSPECTION_LIST_FIELDS
            for item in cleaned[field]
            if field != "uncertainties"
        ).strip()
        require(
            len(evidence) >= 80,
            "insufficient_pixel_evidence",
            PIXEL_INSPECTION_FAILURE,
            image_id=result_id,
        )
        require(
            evidence.lower() not in GENERIC_INSPECTION_PHRASES,
            "generic_inspection_acknowledgement",
            PIXEL_INSPECTION_FAILURE,
            image_id=result_id,
        )
        by_id[result_id] = cleaned

    require(
        set(by_id) == expected_ids,
        "incomplete_inspection",
        PIXEL_INSPECTION_FAILURE,
        missing_image_ids=sorted(expected_ids - set(by_id)),
    )
    return [by_id[image["id"]] for image in images]


def verify_fingerprints(images: Sequence[Dict[str, Any]]) -> None:
    for image in images:
        fingerprint = image.get("fingerprint")
        require(
            isinstance(fingerprint, dict),
            "missing_fingerprint",
            "Inspection state is missing an image fingerprint.",
        )
        if image.get("source_type") != "path":
            continue
        current = fingerprint_source("path", image["source"])
        require(
            current.get("sha256") == fingerprint.get("sha256")
            and current.get("byte_size") == fingerprint.get("byte_size"),
            "source_changed_after_inspection",
            "A local source image changed after pixel inspection. Inspect it again before generation.",
            image_id=image.get("id"),
        )


def compact_text(value: Any, limit: int = 240) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def flattened_strings(value: Any) -> List[str]:
    if isinstance(value, str):
        text = compact_text(value, 1000)
        return [text] if text else []
    if isinstance(value, list):
        result: List[str] = []
        for item in value:
            result.extend(flattened_strings(item))
        return result
    if isinstance(value, dict):
        result = []
        for item in value.values():
            result.extend(flattened_strings(item))
        return result
    return []


def inspection_evidence(result: Dict[str, Any]) -> str:
    parts: List[str] = []
    for field in INSPECTION_LIST_FIELDS:
        parts.extend(flattened_strings(result.get(field)))
    return " ".join(parts).lower()


def keyword_score(text: str, cues: Sequence[str]) -> int:
    return sum(1 for cue in cues if cue.lower() in text)


def first_visible(values: Any, fallback: str, limit: int = 180) -> str:
    for item in flattened_strings(values):
        if item:
            return compact_text(item, limit)
    return fallback


def normalize_style_name(value: Any, field: str, allow_auto: bool = True) -> str:
    if value is None:
        return "auto" if allow_auto else ""
    require(isinstance(value, str), "invalid_style", f"{field} must be a string.")
    normalized = STYLE_ALIASES.get(" ".join(value.strip().lower().replace("-", " ").split()))
    if normalized is None:
        normalized = STYLE_ALIASES.get(value.strip().lower())
    require(normalized is not None, "invalid_style", f"Unsupported {field}.", value=value)
    if not allow_auto:
        require(normalized != "auto", "invalid_style", f"{field} cannot be auto.")
    return normalized


def extract_user_direction(request: Dict[str, Any]) -> str:
    candidates = [request.get("brief"), request.get("request"), request.get("prompt")]
    directions = [compact_text(value, 2000) for value in candidates if isinstance(value, str) and value.strip()]
    return directions[0] if directions else "Create a source-faithful Y2K collage poster from the supplied images."


def build_asset_board(
    state_images: Sequence[Dict[str, Any]],
    inspection_results: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    results_by_id = {result.get("id"): result for result in inspection_results if isinstance(result, dict)}
    use_multi_image_quality_weighting = len(state_images) >= 2
    board: List[Dict[str, Any]] = []
    for index, image in enumerate(state_images):
        result = results_by_id.get(image.get("id"))
        require(isinstance(result, dict), "missing_asset_evidence", "Inspection state lacks source evidence.")
        dimensions = result.get("pixel_dimensions")
        require(isinstance(dimensions, dict), "missing_asset_dimensions", "Inspection state lacks dimensions.")
        width = dimensions.get("width")
        height = dimensions.get("height")
        require(
            isinstance(width, int) and width > 0 and isinstance(height, int) and height > 0,
            "invalid_asset_dimensions",
            "Inspection state contains invalid dimensions.",
            image_id=image.get("id"),
        )
        megapixels = (width * height) / 1_000_000.0
        short_edge = min(width, height)
        condition_text = " ".join(flattened_strings(result.get("image_condition"))).lower()
        visibly_poor = any(cue in condition_text for cue in POOR_QUALITY_CUES)
        visibly_clear = any(cue in condition_text for cue in CLEAR_QUALITY_CUES)
        low_pixel = use_multi_image_quality_weighting and (short_edge < 900 or megapixels < 1.0)
        hero_capable = (
            use_multi_image_quality_weighting
            and short_edge >= 1200
            and megapixels >= 2.0
            and not visibly_poor
        )
        if not use_multi_image_quality_weighting:
            tier = "single-source identity anchor"
        elif visibly_poor:
            tier = "low-quality edge source"
        elif hero_capable:
            tier = "hero-capable"
        elif low_pixel:
            tier = "low-pixel supporting source"
        else:
            tier = "supporting-quality"

        score = min(megapixels, 12.0) + min(short_edge / 600.0, 5.0)
        score += 3.0 if hero_capable else 0.0
        score += 1.0 if visibly_clear else 0.0
        score -= 5.0 if visibly_poor and use_multi_image_quality_weighting else 0.0
        score -= 2.0 if low_pixel else 0.0
        subjects = flattened_strings(result.get("visible_subjects"))
        objects = flattened_strings(result.get("visible_objects"))
        score += 1.0 if subjects else 0.0
        score += 0.25 if objects else 0.0

        board.append(
            {
                "id": image["id"],
                "image_number": index + 1,
                "must_use": bool(image.get("must_use")),
                "pixel_dimensions": {"width": width, "height": height},
                "megapixels": round(megapixels, 2),
                "short_edge": short_edge,
                "quality_tier": tier,
                "hero_capable": hero_capable,
                "low_pixel": low_pixel,
                "visibly_poor": visibly_poor,
                "multi_image_quality_weighting": use_multi_image_quality_weighting,
                "quality_score": round(score, 3),
                "visible_subjects": subjects[:3],
                "visible_objects": objects[:3],
                "identity_locks": flattened_strings(result.get("identity_attributes"))[:4],
                "relationship_locks": flattened_strings(result.get("visible_positions_and_interactions"))[:3],
                "extractable_units": flattened_strings(result.get("extractable_units"))[:4],
                "crop_opportunities": flattened_strings(result.get("crop_opportunities"))[:3],
                "composition": flattened_strings(result.get("composition"))[:3],
                "future_cues": flattened_strings(result.get("future_cues"))[:3],
                "spatial_affordances": flattened_strings(result.get("spatial_affordances"))[:3],
                "image_condition": flattened_strings(result.get("image_condition"))[:3],
                "uncertainties": flattened_strings(result.get("uncertainties"))[:3],
                "evidence_text": inspection_evidence(result),
            }
        )
    return board


def requested_role_id(
    request: Dict[str, Any],
    asset_board: Sequence[Dict[str, Any]],
    field: str,
    reference_role_names: Set[str],
) -> Optional[str]:
    valid_ids = {str(item["id"]) for item in asset_board}
    direct = request.get(field)
    if direct is not None:
        require(isinstance(direct, str) and direct in valid_ids, "invalid_source_role_id", f"{field} must name an inspected image id.")
        return direct

    matches: List[str] = []
    raw_references = request.get("reference_images")
    if isinstance(raw_references, list):
        for raw in raw_references:
            if not isinstance(raw, dict):
                continue
            image_id = raw.get("id")
            role = raw.get("role")
            if not isinstance(image_id, str) or image_id not in valid_ids or not isinstance(role, str):
                continue
            normalized_role = " ".join(role.strip().lower().replace("_", "-").split())
            if normalized_role in reference_role_names:
                matches.append(image_id)
    unique_matches = list(dict.fromkeys(matches))
    require(
        len(unique_matches) <= 1,
        "ambiguous_source_role",
        f"Only one image may be designated through {field} or its equivalent reference role.",
        image_ids=unique_matches,
    )
    return unique_matches[0] if unique_matches else None


def assign_source_roles(asset_board: List[Dict[str, Any]], user_direction: str, request: Dict[str, Any]) -> None:
    require(bool(asset_board), "empty_asset_board", "No inspected images are available for planning.")
    ranked = sorted(asset_board, key=lambda item: (-float(item["quality_score"]), item["image_number"]))
    explicit_hero_id = requested_role_id(
        request,
        asset_board,
        "hero_image_id",
        {"hero", "primary", "primary subject", "main subject", "主角", "主视觉"},
    )
    explicit_cohero_id = requested_role_id(
        request,
        asset_board,
        "cohero_image_id",
        {"co-hero", "cohero", "secondary hero", "shared hero", "联合主角", "副主角"},
    )
    require(
        explicit_hero_id is None or explicit_hero_id != explicit_cohero_id,
        "duplicate_source_role",
        "Hero and co-hero must be different images.",
    )
    hero = next((item for item in asset_board if item["id"] == explicit_hero_id), ranked[0])

    shared_terms = ["co-hero", "cohero", "shared emphasis", "equal emphasis", "two heroes", "双主角", "共同主体", "并列主体"]
    wants_cohero = any(term in user_direction.lower() for term in shared_terms)
    cohero_id = explicit_cohero_id
    if cohero_id is None and wants_cohero:
        candidates = [item for item in ranked if item["id"] != hero["id"]]
        preferred = [item for item in candidates if item["must_use"] and not item["visibly_poor"]]
        if not preferred:
            preferred = [item for item in candidates if not item["visibly_poor"]]
        if preferred:
            cohero_id = str(preferred[0]["id"])

    hero_capable_source_exists = any(item["hero_capable"] for item in asset_board)
    echo_number = 0
    for item in asset_board:
        if item["id"] == hero["id"]:
            item["source_role"] = "hero"
            item["treatment_level"] = "fidelity"
            item["placement"] = "dominant subject field"
            item["selected_for_generation"] = True
        elif item["id"] == cohero_id:
            item["source_role"] = "co-hero"
            item["treatment_level"] = "fidelity"
            item["placement"] = "shared subject field"
            item["selected_for_generation"] = True
        elif hero_capable_source_exists and (item["visibly_poor"] or item["low_pixel"]):
            item["source_role"] = "peripheral detail source"
            item["treatment_level"] = "experimental"
            item["placement"] = "small edge card or interface fragment, roughly 5–15% of poster area"
            item["selected_for_generation"] = bool(item["must_use"])
        else:
            echo_number += 1
            item["source_role"] = "echo" if echo_number <= 2 else "detail source"
            item["treatment_level"] = "translation"
            item["placement"] = "supporting annotation field"
            item["selected_for_generation"] = True


def route_style(
    asset_board: Sequence[Dict[str, Any]],
    request: Dict[str, Any],
    user_direction: str,
    creative_context: str = "",
    select_supporting: bool = True,
) -> Tuple[str, Optional[str], Dict[str, int]]:
    evidence = " ".join(
        [user_direction.lower(), creative_context.lower()]
        + [str(item.get("evidence_text", "")) for item in asset_board]
    )
    scores: Dict[str, int] = {}
    for style_id in STYLE_ORDER:
        scores[style_id] = keyword_score(evidence, STYLE_FAMILIES[style_id]["cues"])

    explicit = normalize_style_name(request.get("style", "auto"), "style", allow_auto=True)
    if explicit != "auto":
        primary = explicit
    else:
        primary = max(STYLE_ORDER, key=lambda style_id: (scores[style_id], -STYLE_ORDER.index(style_id)))

    supporting: Optional[str] = None
    requested_support = request.get("supporting_style")
    if select_supporting and requested_support is not None:
        supporting = normalize_style_name(requested_support, "supporting_style", allow_auto=False)
        require(supporting != primary, "duplicate_style", "Supporting style must differ from the primary style.")
        require(
            (primary, supporting) in SUPPORTING_PAIR_RULES,
            "unsupported_style_pair",
            "The requested supporting style would compete with the primary style instead of contributing one bounded subsystem.",
            primary_style=primary,
            supporting_style=supporting,
        )
    elif select_supporting and explicit == "auto":
        runners = [
            style_id
            for style_id in STYLE_ORDER
            if style_id != primary and (primary, style_id) in SUPPORTING_PAIR_RULES
        ]
        if not runners:
            return primary, None, scores
        runner = max(runners, key=lambda style_id: (scores[style_id], -STYLE_ORDER.index(style_id)))
        # A close score is not enough by itself: the approved pair supplies a
        # concrete, non-competing subsystem, and the supporting family must
        # also have substantial visible evidence.
        if scores[primary] >= 5 and scores[runner] >= 4 and scores[runner] >= scores[primary] - 1:
            supporting = runner
    return primary, supporting, scores


def choose_scored_option(evidence: str, options: Dict[str, Sequence[str]], fallback: str) -> Tuple[str, Dict[str, int]]:
    scores = {name: keyword_score(evidence, cues) for name, cues in options.items()}
    best = max(options, key=lambda name: scores[name])
    if scores[best] == 0:
        best = fallback
    return best, scores


def choose_stage_and_material(
    asset_board: Sequence[Dict[str, Any]],
    primary_style: str,
    user_direction: str,
) -> Tuple[str, str]:
    evidence = " ".join([user_direction.lower()] + [str(item.get("evidence_text", "")) for item in asset_board])
    style = STYLE_FAMILIES[primary_style]
    stage_fallback = style["preferred_stages"][0]
    material_fallback = style["preferred_materials"][0]
    stage, stage_scores = choose_scored_option(evidence, STAGE_CUES, stage_fallback)
    material, material_scores = choose_scored_option(evidence, MATERIAL_CUES, material_fallback)
    if primary_style == "techno_pop_campaign":
        biased_stage_scores = dict(stage_scores)
        biased_material_scores = dict(material_scores)
        for preferred_stage in style["preferred_stages"]:
            biased_stage_scores[preferred_stage] = biased_stage_scores.get(preferred_stage, 0) + 2
        for preferred_material in style["preferred_materials"]:
            biased_material_scores[preferred_material] = biased_material_scores.get(preferred_material, 0) + 2
        stage = max(STAGE_CUES, key=lambda name: biased_stage_scores[name])
        material = max(MATERIAL_CUES, key=lambda name: biased_material_scores[name])
    return stage, material


def choose_emotional_tension(evidence: str) -> str:
    tension_cues: List[Tuple[str, List[str]]] = [
        ("connection versus isolation", ["alone", "single", "distance", "screen", "phone", "network", "孤独", "独自"]),
        ("organic versus synthetic", ["plant", "water", "animal", "flora", "organic", "nature", "植物", "自然"]),
        ("play versus control", ["playful", "toy", "game", "bright", "smile", "colorful", "游戏", "玩具"]),
        ("intimacy versus surveillance", ["close-up", "gaze", "camera", "scan", "face", "portrait", "凝视", "镜头"]),
        ("human identity versus machine classification", ["diagnostic", "laboratory", "device", "machine", "technical", "机器", "识别"]),
        ("speed versus suspension", ["vehicle", "rail", "road", "motion", "transit", "movement", "车辆", "移动"]),
    ]
    ranked = [(keyword_score(evidence, cues), -index, label) for index, (label, cues) in enumerate(tension_cues)]
    score, _, label = max(ranked)
    return label if score > 0 else "nostalgia versus an unrealized future"


def choose_aspect_ratio(asset_board: Sequence[Dict[str, Any]], request: Dict[str, Any]) -> Tuple[str, str]:
    canvas = request.get("canvas")
    if isinstance(canvas, dict) and canvas.get("aspect_ratio") is not None:
        ratio = canvas.get("aspect_ratio")
        require(
            isinstance(ratio, str) and RATIO_PATTERN.fullmatch(ratio) is not None,
            "invalid_aspect_ratio",
            "Canvas aspect_ratio must use a positive W:H form.",
        )
        return ratio, "locked by the user request"

    hero = next((item for item in asset_board if item.get("source_role") == "hero"), asset_board[0])
    width = int(hero["pixel_dimensions"]["width"])
    height = int(hero["pixel_dimensions"]["height"])
    evidence = str(hero.get("evidence_text", ""))
    must_use_count = sum(1 for item in asset_board if item.get("must_use"))
    if height > width * 1.18:
        if any(cue in evidence for cue in ["full body", "full-body", "standing", "vertical", "long silhouette"]):
            return "2:3", "chosen from the vertical full-subject silhouette and crop safety"
        if must_use_count >= 3:
            return "4:5", "chosen to hold several must-use sources without destructive vertical cropping"
        return "3:4", "chosen from the portrait-oriented hero and available annotation space"
    if width > height * 1.18:
        if must_use_count >= 3:
            return "3:2", "chosen to distribute several must-use sources across a wide hierarchy"
        return "5:3", "chosen from the landscape hero, lateral movement, and breathing room"
    return "1:1", "chosen from the near-square source balance and compact collage hierarchy"


def normalize_text_plan(
    request: Dict[str, Any],
    primary_style: str,
    asset_board: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    raw = request.get("text")
    headline = ""
    micro_labels: List[str] = []
    if isinstance(raw, str):
        headline = compact_text(raw, 120)
    elif isinstance(raw, dict):
        headline_value = raw.get("headline", "")
        require(isinstance(headline_value, str), "invalid_text", "text.headline must be a string.")
        headline = compact_text(headline_value, 120)
        labels = raw.get("micro_labels", [])
        require(isinstance(labels, list), "invalid_text", "text.micro_labels must be a list.")
        for label in labels[:3]:
            require(isinstance(label, str), "invalid_text", "Every micro-label must be a string.")
            cleaned = compact_text(label, 40)
            if cleaned:
                micro_labels.append(cleaned)
    else:
        require(raw is None, "invalid_text", "text must be a string or object.")

    allow_authored_value = request.get("allow_authored_text")
    require(
        allow_authored_value is None or isinstance(allow_authored_value, bool),
        "invalid_authored_text",
        "allow_authored_text must be boolean when supplied.",
    )
    selected_count = sum(1 for item in asset_board if item.get("selected_for_generation") is True)
    dense_source_field = selected_count >= 3
    route_benefits_from_headline = primary_style in {
        "pop_scrapbook",
        "punk_halftone",
        "liquid_chrome_futurism",
        "techno_pop_campaign",
    }
    if allow_authored_value is True:
        author_headline = not headline
    elif allow_authored_value is False:
        author_headline = False
    else:
        author_headline = not headline and route_benefits_from_headline and not dense_source_field

    if author_headline:
        authored = {
            "pop_scrapbook": "FUTURE IN REPLAY",
            "webcore_desktop": "MEMORY ONLINE",
            "punk_halftone": "SIGNAL UNDER PRESSURE",
            "liquid_chrome_futurism": "MIRROR THE FUTURE",
            "techno_pop_campaign": "SOFT SYSTEM",
        }
        headline = authored[primary_style]

    allow_structural_labels = allow_authored_value is not False
    if allow_structural_labels and not micro_labels and primary_style == "webcore_desktop":
        micro_labels = ["ONLINE", "SIGNAL", "READY"]
    elif allow_structural_labels and not micro_labels and primary_style == "techno_pop_campaign":
        micro_labels = ["READY", "MEMORY"]
    return {
        "headline": headline,
        "micro_labels": micro_labels,
        "authored": bool(raw is None and (author_headline or micro_labels)),
        "authored_text_mode": (
            "enabled" if allow_authored_value is True else "disabled" if allow_authored_value is False else "auto"
        ),
        "dense_source_field": dense_source_field,
    }


def future_premise_for(
    stage: str,
    material: str,
    tension: str,
    asset_board: Sequence[Dict[str, Any]],
    primary_style: str,
) -> str:
    hero = next((item for item in asset_board if item.get("source_role") == "hero"), asset_board[0])
    cue = first_visible(hero.get("future_cues"), first_visible(hero.get("visible_objects"), "a visible source detail"), 140)
    templates = {
        "flat editorial field": "The source subject appears as a turn-of-the-millennium editorial identity assembled from memory fragments",
        "desktop or interface space": "The source subject persists as a personal image being replayed inside an early networked desktop",
        "nocturnal city or transit space": "The source subject pauses inside a networked transit threshold imagined near the millennium",
        "synthetic laboratory": "The source subject is presented as an identity prototype being calibrated inside a friendly but intrusive laboratory",
        "product or industrial void": "The source subject and its visible prop become a prototype display inside a sparse engineered showroom",
        "cosmic or atmospheric zone": "The source subject survives as a transmitted portrait inside an artificial signal atmosphere",
        "bio-tech habitat": "The source subject enters a synthetic habitat where organic traces and digital systems coexist",
    }
    clean_cue = cue.rstrip(" .;:")
    if primary_style == "techno_pop_campaign":
        return (
            "The source subject becomes the star of an imagined turn-of-the-millennium consumer-tech campaign "
            f"whose oversized product world extends from the visible cue: {clean_cue}; express {tension} "
            f"through {material}."
        )
    return f"{templates[stage]}, extending from the visible cue: {clean_cue}; express {tension} through {material}."


def supporting_subsystem(primary: str, supporting: Optional[str]) -> str:
    if supporting is None:
        return "none"
    rule = SUPPORTING_PAIR_RULES.get((primary, supporting))
    require(rule is not None, "unsupported_style_pair", "No bounded supporting subsystem exists for this style pair.")
    return rule["subsystem"]


def supporting_purpose(primary: str, supporting: Optional[str]) -> str:
    if supporting is None:
        return "none"
    rule = SUPPORTING_PAIR_RULES.get((primary, supporting))
    require(rule is not None, "unsupported_style_pair", "No bounded supporting purpose exists for this style pair.")
    return rule["purpose"]


def build_creative_plan(state: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
    state_images = state.get("images")
    inspection_results = state.get("inspection_results")
    require(isinstance(state_images, list) and state_images, "invalid_state_images", "Inspection state has no images.")
    require(
        isinstance(inspection_results, list) and inspection_results,
        "missing_inspection_results",
        "Inspection state has no pixel-grounded analysis.",
    )
    user_direction = extract_user_direction(request)
    asset_board = build_asset_board(state_images, inspection_results)
    assign_source_roles(asset_board, user_direction, request)
    explicit_references = request.get("reference_images")
    if isinstance(explicit_references, list):
        explicit_ids = {
            item.get("id") for item in explicit_references if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        for item in asset_board:
            item["selected_for_generation"] = bool(
                item["must_use"]
                or item["id"] in explicit_ids
                or item.get("source_role") in {"hero", "co-hero"}
            )
    evidence = " ".join([user_direction.lower()] + [str(item.get("evidence_text", "")) for item in asset_board])
    tension = choose_emotional_tension(evidence)
    primary, _, _ = route_style(asset_board, request, user_direction, select_supporting=False)

    # Iterate the primary route with the world-building decisions it produces.
    # This makes style selection depend on the future premise, spatial stage,
    # material system, and emotional tension instead of source keywords alone.
    for _ in range(5):
        stage, material = choose_stage_and_material(asset_board, primary, user_direction)
        premise = future_premise_for(stage, material, tension, asset_board, primary)
        creative_context = " ".join([premise, stage, material, tension])
        routed_primary, _, _ = route_style(
            asset_board,
            request,
            user_direction,
            creative_context=creative_context,
            select_supporting=False,
        )
        if routed_primary == primary:
            break
        primary = routed_primary

    stage, material = choose_stage_and_material(asset_board, primary, user_direction)
    premise = future_premise_for(stage, material, tension, asset_board, primary)
    creative_context = " ".join([premise, stage, material, tension])
    primary, supporting, style_scores = route_style(
        asset_board,
        request,
        user_direction,
        creative_context=creative_context,
        select_supporting=True,
    )
    # An explicit primary remains fixed; an automatic route may settle on a
    # different family after context scoring, so rebuild its world once.
    stage, material = choose_stage_and_material(asset_board, primary, user_direction)
    premise = future_premise_for(stage, material, tension, asset_board, primary)
    ratio, ratio_reason = choose_aspect_ratio(asset_board, request)
    text_plan = normalize_text_plan(request, primary, asset_board)
    return {
        "user_direction": user_direction,
        "asset_board": asset_board,
        "canvas": {"aspect_ratio": ratio, "selection_reason": ratio_reason},
        "primary_style": primary,
        "supporting_style": supporting,
        "supporting_subsystem": supporting_subsystem(primary, supporting),
        "supporting_purpose": supporting_purpose(primary, supporting),
        "style_scores": style_scores,
        "future_premise": premise,
        "spatial_stage": stage,
        "material_system": material,
        "emotional_tension": tension,
        "text": text_plan,
    }


def compact_list(values: Sequence[str], fallback: str, limit: int = 3) -> str:
    cleaned = [compact_text(value, 160) for value in values if compact_text(value, 160)]
    return "; ".join(cleaned[:limit]) if cleaned else fallback


def compile_generation_prompt(plan: Dict[str, Any]) -> str:
    board = [item for item in plan["asset_board"] if item.get("selected_for_generation") is True]
    require(bool(board), "empty_generation_board", "Creative planning selected no source images.")
    hero = next(item for item in board if item["source_role"] == "hero")
    primary = STYLE_FAMILIES[plan["primary_style"]]
    supporting_id = plan.get("supporting_style")

    source_blocks: List[str] = []
    operation_blocks: List[str] = []
    for item in board:
        label = f"Image {item['image_number']}"
        locks = compact_list(item["identity_locks"], "preserve every reliably visible identity and object trait")
        relationships = compact_list(item["relationship_locks"], "preserve visible pose, direction, and source associations", 2)
        extractables = compact_list(item["extractable_units"], "one truthful source-derived crop", 3)
        source_blocks.append(
            f"{label} — {item['source_role']}; must-use={str(item['must_use']).lower()}; "
            f"quality tier={item['quality_tier']}; treatment={item['treatment_level']}; "
            f"placement={item['placement']}. Identity locks: {locks}. Relationship locks: {relationships}."
        )
        operation_blocks.append(
            f"From {label}, use {extractables}. Keep it at a scale supported by its visible detail; "
            f"apply {item['treatment_level']} treatment and place it in the {item['placement']}."
        )

    headline = plan["text"]["headline"]
    labels = plan["text"]["micro_labels"]
    if headline:
        text_instruction = f'Reproduce the exact headline "{headline}" without translation or rewriting.'
    else:
        text_instruction = "Use no semantic headline; let the image hierarchy carry the poster."
    if labels:
        quoted_labels = ", ".join(f'"{label}"' for label in labels)
        text_instruction += f" Use only these exact micro-labels: {quoted_labels}."
    else:
        text_instruction += " Do not invent names, dates, credits, quotations, locations, brands, or product claims."

    if supporting_id:
        supporting_clause = (
            f"Use {STYLE_FAMILIES[supporting_id]['label']} only as a supporting family, limited strictly to "
            f"{plan['supporting_subsystem']} for {plan['supporting_purpose']}. Keep it visibly subordinate at "
            "roughly 20–35% of the visible grammar; it must not control the whole world, composition, palette, "
            "portrait treatment, typography, or material behavior."
        )
    else:
        supporting_clause = "Use no supporting style family."

    ratio = plan["canvas"]["aspect_ratio"]
    canvas_block = (
        f"CANVAS AND HIERARCHY — Render a bitmap Y2K collage poster at exact aspect ratio {ratio}; "
        f"{plan['canvas']['selection_reason']}. Build three readable bands: a source-responsive background, "
        f"a dominant subject field led by Image {hero['image_number']}, and a lighter annotation field. "
        "Use at least two scales of source imagery, one meaningful overlap that passes behind and in front of different elements, "
        "one obvious focal entry, a coherent eye path, and one quiet exit area. Preserve active negative space and thumbnail readability."
    )

    source_block = (
        "SOURCE ROLES AND INVARIANTS — " + " ".join(source_blocks) + " "
        "Keep at least one clear fidelity-preserving representation of every must-use person or object. "
        "Never exchange faces, bodies, outfits, props, or multi-person relationships between sources. "
        "Do not invent alternate outfits, poses, events, or source material."
    )

    collage_block = (
        "COLLAGE OPERATIONS — " + " ".join(operation_blocks) + " " + primary["composition"] + " "
        "Use hero clarity as the fidelity layer, recognizable echoes and props as the translation layer, and reserve extreme crops, "
        "pixelation, selection handles, scan lines, compression, diagrams, and texture ghosts for small experimental details. "
        "Every repetition, frame, icon, and invented object must reinforce the subject, answer a visible source cue, connect sources, "
        "guide the eye, balance visual weight, or clarify scale. Remove decorative filler. Keep collage seams, cutouts, frames, and repetitions visible."
    )

    style_block = (
        f"FUTURE, STYLE, MATERIAL, AND TYPE — Future premise: {plan['future_premise']} "
        f"Use {plan['spatial_stage']} as the dominant spatial stage. Use {primary['label']} as the only primary style family. "
        f"{supporting_clause} "
        f"Style-specific visible treatment: {primary.get('directives', 'Follow the selected family composition and source transformations while preserving identity.')} "
        f"Dominant material behavior: {plan['material_system']}. Make light, reflection, transparency, shadow, edge quality, and surface response obey it. "
        f"Express {plan['emotional_tension']} through hierarchy and atmosphere. Global palette: {primary['palette']}. "
        f"Typography system: {primary['type']}. {text_instruction} "
        "Harmonize source photos through shared palette, edge behavior, resolution hierarchy, and reproduction texture while preserving distinctive skin, clothing, and prop colors."
    )

    avoids = "; ".join(
        [
            primary["avoid"],
            "text-only likeness substitution",
            "unrelated extra people",
            "identity drift or face–body swaps",
            "random motif piles and equal-sized photo grids",
            "several competing style systems",
            "generic purple-neon city scenery and random foreign-script decoration",
            "polished contemporary application interfaces",
            "copied logos, watermarks, fake credits, and illegible pseudo-copy",
            "uniform sharpness or uniform distress",
            "one-click global tinting",
            "seamless blockbuster concept art that erases the collage construction",
        ]
    )
    fidelity_block = (
        f"FIDELITY AND HARD AVOIDS — Follow the user direction: {plan['user_direction']} "
        f"Preserve source-specific face structure, hair, clothing, pose, expression, object geometry, and visible associations. "
        f"Do not enlarge weak sources beyond reliable detail. Avoid: {avoids}. "
        "The final result must read as one intentionally dense but legible, source-faithful Y2K collage poster, not a generic science-fiction scene."
    )
    return "\n\n".join([canvas_block, source_block, collage_block, style_block, fidelity_block])


def plan_reference_roles(plan: Dict[str, Any]) -> Dict[str, str]:
    roles: Dict[str, str] = {}
    for item in plan["asset_board"]:
        if item.get("selected_for_generation") is not True:
            continue
        roles[item["id"]] = (
            f"{item['source_role']}; {item['treatment_level']} treatment; {item['placement']}; "
            f"quality tier {item['quality_tier']}"
        )
    return roles


def normalize_reference_images(
    request: Dict[str, Any],
    state_images: Sequence[Dict[str, Any]],
    planned_roles: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    raw_refs = request.get("reference_images")
    if raw_refs is None:
        if planned_roles:
            raw_refs = [{"id": image["id"]} for image in state_images if image["id"] in planned_roles]
        else:
            raw_refs = [{"id": image["id"]} for image in state_images if image.get("must_use") is True]
        if not raw_refs:
            raw_refs = [{"id": image["id"]} for image in state_images]
    require(isinstance(raw_refs, list) and raw_refs, "missing_reference_images", REFERENCE_GENERATION_FAILURE)
    state_by_id = {image["id"]: image for image in state_images}
    references: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for index, raw in enumerate(raw_refs):
        require(isinstance(raw, dict), "invalid_reference_entry", REFERENCE_GENERATION_FAILURE, index=index)
        image_id = raw.get("id")
        require(image_id in state_by_id, "uninspected_reference", REFERENCE_GENERATION_FAILURE, image_id=image_id)
        require(image_id not in seen, "duplicate_reference", REFERENCE_GENERATION_FAILURE, image_id=image_id)
        role = raw.get("role")
        if role is None and planned_roles is not None:
            role = planned_roles.get(str(image_id))
        require(
            isinstance(role, str) and role.strip(),
            "missing_reference_role",
            "Each reference image needs a visible role.",
            image_id=image_id,
        )
        image = state_by_id[image_id]
        references.append(
            {
                "id": image_id,
                "source": image["source"],
                "source_type": image["source_type"],
                "role": role.strip(),
                "must_use": image["must_use"],
            }
        )
        seen.add(image_id)

    must_use_ids = {image["id"] for image in state_images if image.get("must_use") is True}
    require(
        must_use_ids.issubset(seen),
        "missing_must_use_reference",
        REFERENCE_GENERATION_FAILURE,
        missing_image_ids=sorted(must_use_ids - seen),
    )
    if planned_roles is not None:
        identity_anchor_ids = {
            image_id
            for image_id, role in planned_roles.items()
            if role.startswith("hero;") or role.startswith("co-hero;")
        }
        require(
            identity_anchor_ids.issubset(seen),
            "missing_identity_anchor_reference",
            REFERENCE_GENERATION_FAILURE,
            missing_image_ids=sorted(identity_anchor_ids - seen),
        )
    return references


def normalize_canvas(request: Dict[str, Any], fallback_ratio: Optional[str] = None) -> Dict[str, str]:
    canvas = request.get("canvas")
    if canvas is None and fallback_ratio is not None:
        ratio = fallback_ratio
    else:
        require(isinstance(canvas, dict), "missing_canvas", "Generation request must contain a canvas object.")
        ratio = canvas.get("aspect_ratio")
    require(
        isinstance(ratio, str) and RATIO_PATTERN.fullmatch(ratio) is not None,
        "invalid_aspect_ratio",
        "Canvas aspect_ratio must use a positive W:H form.",
    )
    return {"aspect_ratio": ratio}


def normalize_output(request: Dict[str, Any]) -> Dict[str, str]:
    output = request.get("output")
    if output is None:
        output = {"format": "png"}
    require(isinstance(output, dict), "missing_output", "Generation request output must be an object.")
    image_format = output.get("format", "png")
    require(
        isinstance(image_format, str) and FORMAT_PATTERN.fullmatch(image_format) is not None,
        "invalid_output_format",
        "Output format must be a short format identifier.",
    )
    return {"format": image_format.lower()}


def normalize_correction(value: Any) -> Optional[Dict[str, str]]:
    if value is None:
        return None
    require(isinstance(value, dict), "invalid_correction", "correction must be an object.")
    required = ["keep_unchanged", "correct_only", "required_visible_change", "do_not_introduce"]
    correction: Dict[str, str] = {}
    for field in required:
        text = value.get(field)
        require(
            isinstance(text, str) and text.strip(),
            "invalid_correction",
            "Correction fields must be non-empty strings.",
            field=field,
        )
        correction[field] = text.strip()
    return correction


def validate_generated_image(response: Dict[str, Any], required_ids: Set[str]) -> Dict[str, str]:
    require(response.get("contract") == GENERATION_CONTRACT, "wrong_generation_contract", REFERENCE_GENERATION_FAILURE)
    require(response.get("status") == "success", "generation_failed", "Generation adapter did not report success.")
    used = response.get("used_reference_images")
    require(
        isinstance(used, list) and all(isinstance(item, str) for item in used),
        "missing_reference_confirmation",
        REFERENCE_GENERATION_FAILURE,
    )
    used_ids = set(used)
    require(
        required_ids.issubset(used_ids),
        "unconfirmed_reference_use",
        REFERENCE_GENERATION_FAILURE,
        missing_image_ids=sorted(required_ids - used_ids),
    )

    image = response.get("image")
    require(isinstance(image, dict), "missing_generated_image", "Generation adapter did not return an image locator.")
    locator_type = image.get("type")
    locator_value = image.get("value")
    require(
        locator_type in IMAGE_LOCATOR_TYPES,
        "invalid_image_locator",
        "Generated image locator type is unsupported.",
    )
    require(
        isinstance(locator_value, str) and locator_value.strip(),
        "invalid_image_locator",
        "Generated image locator is empty.",
    )
    locator_value = locator_value.strip()
    if locator_type == "path":
        output_path = Path(locator_value).expanduser().resolve()
        require(
            output_path.is_file() and output_path.stat().st_size > 0,
            "missing_generated_file",
            "Generation adapter returned a missing or empty image file.",
            path=str(output_path),
        )
        locator_value = str(output_path)
    elif locator_type == "base64":
        try:
            decoded = base64.b64decode(locator_value, validate=True)
        except (ValueError, TypeError):
            raise RunnerError(
                "invalid_base64_image",
                "Generation adapter returned invalid base64 image content.",
            )
        require(bool(decoded), "empty_generated_image", "Generation adapter returned empty image content.")
    return {"type": locator_type, "value": locator_value}


def validate_quality_response(response: Dict[str, Any]) -> Dict[str, Any]:
    require(
        response.get("contract") == INSPECTION_CONTRACT,
        "wrong_quality_contract",
        "Output inspection adapter returned the wrong contract.",
    )
    quality_gate = response.get("quality_gate")
    require(
        isinstance(quality_gate, dict),
        "missing_quality_gate",
        "Output inspection did not return a quality_gate object.",
    )
    passed = quality_gate.get("passed")
    require(isinstance(passed, bool), "invalid_quality_gate", "quality_gate.passed must be boolean.")
    failures = list_of_strings(quality_gate.get("failures"), "quality_gate.failures", allow_empty=True)
    observations = list_of_strings(response.get("observations"), "observations", allow_empty=False)
    require(
        len(" ".join(observations)) >= 80,
        "insufficient_quality_evidence",
        "Output quality inspection lacks pixel-grounded evidence.",
    )
    correction = quality_gate.get("targeted_correction")
    normalized_correction = normalize_correction(correction) if correction is not None else None
    if passed:
        require(not failures, "contradictory_quality_gate", "A passing quality gate must not contain failures.")
    else:
        require(
            bool(failures),
            "missing_quality_failures",
            "A failing quality gate must explain the visible failure.",
        )
    return {
        "passed": passed,
        "failures": failures,
        "observations": observations,
        "targeted_correction": normalized_correction,
    }


def quality_requirements(plan: Dict[str, Any]) -> Dict[str, Any]:
    checks = [
        "every must-use source is visibly represented and recognizable",
        "faces, bodies, outfits, props, and visible relationships remain correctly associated",
        "weak sources are not enlarged beyond reliable detail when a stronger hero exists",
        "one clear hero or intentionally shared co-hero hierarchy is visible",
        "at least two source-image scales and one meaningful overlap are visible",
        "every repetition has a compositional role",
        "the primary style is dominant and any supporting style remains one bounded subsystem occupying roughly 20–35% of the visible grammar",
        "the future premise responds to visible source cues instead of generic science-fiction motifs",
        "foreground, subject field, and background remain distinguishable",
        "the eye path and identity anchor remain readable at thumbnail size",
        "palette, edge behavior, sharpness hierarchy, texture, light, and material response are coherent",
        "supplied text is exact and no names, dates, credits, brands, or factual claims were invented",
        "no watermark, accidental border, extra person, anatomy error, or illegible pseudo-copy is visible",
        "the result remains visibly constructed as a collage rather than seamless concept art",
    ]
    if plan["primary_style"] == "techno_pop_campaign":
        checks.extend(
            [
                "an oversized source-responsive consumer device forms a spatial stage and visibly interacts with the hero rather than appearing as detached gadget stickers",
                "the hero portrait has heightened facial and hair contrast, slightly richer source-faithful color, and controlled mild highlight bloom while retaining recognizable facial geometry and natural texture",
                "the main face remains clearer than the processed echoes and is not illustrated, doll-like, plastic, melted, excessively smoothed, or clipped by overexposure",
                "one dominant campaign color, one contrasting dark, and engineered white, silver, grey, or transparent neutrals unify the product world",
                "any game-cover or product-mark title is short, legible, generic, subordinate to the identity anchor, and does not reproduce a real logo",
                "the result reads as turn-of-the-millennium consumer-tech advertising rather than a flat catalog, modern luxury campaign, clean contemporary interface, or seamless product render",
            ]
        )
    return {
        "canvas_aspect_ratio": plan["canvas"]["aspect_ratio"],
        "primary_style": STYLE_FAMILIES[plan["primary_style"]]["label"],
        "supporting_style": (
            STYLE_FAMILIES[plan["supporting_style"]]["label"] if plan.get("supporting_style") else None
        ),
        "future_premise": plan["future_premise"],
        "spatial_stage": plan["spatial_stage"],
        "material_system": plan["material_system"],
        "emotional_tension": plan["emotional_tension"],
        "exact_text": plan["text"],
        "source_roles": [
            {
                "id": item["id"],
                "source_role": item["source_role"],
                "quality_tier": item["quality_tier"],
                "treatment_level": item["treatment_level"],
                "must_use": item["must_use"],
            }
            for item in plan["asset_board"]
            if item.get("selected_for_generation") is True
        ],
        "checks": checks,
    }


def derive_targeted_correction(quality: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, str]:
    failures = quality.get("failures") or ["the visible quality-gate failure"]
    observed = compact_text(str(failures[0]), 300)
    lower = " ".join(flattened_strings(failures) + flattened_strings(quality.get("observations"))).lower()
    remedies: List[Tuple[List[str], str, str]] = [
        (
            ["plastic face", "doll-like", "doll like", "over-smoothed", "oversmoothed", "melted face", "highlight clipping", "overexposure"],
            "the overprocessed hero face",
            "restore recognizable facial geometry and natural texture, reduce smoothing and highlight clipping, keep crisp dark features, and confine stronger effects to small replays",
        ),
        (
            ["untouched portrait", "natural portrait", "not stylized", "portrait treatment", "commercial glamour"],
            "the Techno Pop portrait treatment",
            "retain the source-specific face while increasing facial and hair contrast, slightly enriching natural skin and makeup color, and adding controlled mild hard-flash bloom without erasing texture",
        ),
        (
            ["gadget sticker", "detached device", "product stage", "device interaction", "flat catalog", "hardware stage"],
            "the consumer-device spatial stage",
            "turn one source-responsive oversized device into readable architecture that passes behind and in front of the hero, and remove unrelated detached gadget decorations",
        ),
        (
            ["modern luxury", "contemporary product", "clean ui", "clean interface", "seamless product render"],
            "the period-specific campaign language",
            "restore a deliberately artificial turn-of-the-millennium campaign using hard flash, molded consumer plastic, visible collage seams, early-digital reproduction artifacts, and product-mark hierarchy",
        ),
        (
            ["identity", "face", "hair", "outfit", "pose", "recognizable"],
            "the hero identity",
            "restore the source-specific face structure, hair, clothing, pose, and recognizable object geometry while reducing treatment over the fidelity hero",
        ),
        (
            ["association", "swapped", "body", "prop", "relationship"],
            "source associations",
            "restore which face, body, outfit, and prop belong together and preserve the visible source relationships",
        ),
        (
            ["generic", "y2k", "motif", "future", "science-fiction"],
            "the generic visual language",
            "replace arbitrary motifs with source-responsive crops, repetitions, interfaces, props, and a clearer source-derived future premise",
        ),
        (
            ["material", "reflection", "transparency", "lighting"],
            "material coherence",
            "make reflections, transparency, glow, edges, shadows, and light direction obey the one dominant material system",
        ),
        (
            ["style", "collision", "competing"],
            "the style collision",
            "restore the selected primary style and confine the supporting style to its one declared subsystem",
        ),
        (
            ["flat", "depth", "overlap", "scale"],
            "the flat collage hierarchy",
            "increase scale contrast, create one clear behind-and-in-front overlap, and separate foreground, subject field, and background",
        ),
        (
            ["clutter", "density", "motif overload", "eye path", "thumbnail"],
            "visual clutter",
            "remove at least one third of small decorative elements, preserve the hero and meaningful source crops, and restore a quiet exit area",
        ),
        (
            ["text", "spelling", "letter", "pseudo-copy"],
            "the text failure",
            "restore the exact supplied wording, remove illegible pseudo-copy, and reduce competing labels",
        ),
        (
            ["color", "palette", "fragment"],
            "color fragmentation",
            "reduce the palette families and repeat the primary contrast color across source imagery, graphics, and type",
        ),
        (
            ["weak source", "low-resolution", "low pixel", "blurred source"],
            "weak-source dominance",
            "shrink the weak source into a peripheral card, crop, or interface fragment and restore the strongest source as the clear identity anchor",
        ),
    ]
    target = observed
    visible_change = f"visibly correct only this observed failure: {observed}"
    for cues, candidate_target, candidate_change in remedies:
        if any(cue in lower for cue in cues):
            target = candidate_target
            visible_change = candidate_change
            break
    primary = STYLE_FAMILIES[plan["primary_style"]]["label"]
    return {
        "keep_unchanged": (
            f"successful source identities, source associations, canvas ratio {plan['canvas']['aspect_ratio']}, "
            f"overall layout, {primary} direction, palette, and any quality-gate checks that already pass"
        ),
        "correct_only": target,
        "required_visible_change": visible_change,
        "do_not_introduce": (
            "new people, changed outfits, face–body swaps, unrelated props, competing styles, new text, copied logos, watermarks, or layout drift"
        ),
    }


def image_locator_as_inspection_input(image: Dict[str, str]) -> Dict[str, Any]:
    return {
        "id": "generated-output",
        "source": image["value"],
        "source_type": image["type"],
        "must_use": True,
        "role": "generated_output",
    }


def cmd_inspect(args: argparse.Namespace) -> Dict[str, Any]:
    state_path = Path(args.state).expanduser().resolve()
    require(
        not state_path.exists(),
        "state_already_exists",
        "Inspection state already exists; use a new path.",
        path=str(state_path),
    )
    request = load_json(Path(args.request).expanduser().resolve())
    images = normalize_source_images(request)

    capabilities = request_capabilities(
        args.adapter,
        args.adapter_arg,
        INSPECTION_CONTRACT,
        args.timeout,
    )
    purposes = capabilities.get("purposes")
    require(
        capabilities.get("pixel_inspection") is True,
        "pixel_inspection_unavailable",
        PIXEL_INSPECTION_FAILURE,
    )
    require(
        isinstance(purposes, list)
        and "source_asset_board" in purposes
        and "output_quality_gate" in purposes,
        "inspection_purpose_unavailable",
        PIXEL_INSPECTION_FAILURE,
    )

    provider_request: Dict[str, Any] = {
        "contract": INSPECTION_CONTRACT,
        "operation": "inspect_images",
        "purpose": "source_asset_board",
        "images": [
            {
                "id": image["id"],
                "source": image["source"],
                "source_type": image["source_type"],
                "must_use": image["must_use"],
            }
            for image in images
        ],
        "analysis_scope": SOURCE_ANALYSIS_SCOPE,
    }
    if isinstance(request.get("provider_options"), dict):
        provider_request["provider_options"] = request["provider_options"]

    response = invoke_adapter(
        args.adapter,
        args.adapter_arg,
        provider_request,
        args.timeout,
    )
    inspection_results = validate_source_inspection_results(response, images)
    state = {
        "contract": RUNNER_CONTRACT,
        "created_at": utc_now(),
        "pixel_inspection": "PASS",
        "reference_conditioned_generation": "PENDING",
        "inspected_image_handles": [image["id"] for image in images],
        "generation_reference_handles": [],
        "generation_attempts": 0,
        "images": images,
        "inspection_results": inspection_results,
    }
    write_json_atomic(state_path, state)
    return {
        "status": "inspection_passed",
        "state": str(state_path),
        "inspected_image_handles": state["inspected_image_handles"],
    }


def cmd_generate(args: argparse.Namespace) -> Dict[str, Any]:
    state_path = Path(args.state).expanduser().resolve()
    result_path = Path(args.result).expanduser().resolve()
    state = load_json(state_path)
    require(state.get("contract") == RUNNER_CONTRACT, "invalid_state_contract", "Inspection state contract is invalid.")
    require(state.get("pixel_inspection") == "PASS", "pixel_inspection_not_passed", PIXEL_INSPECTION_FAILURE)
    state_images = state.get("images")
    require(isinstance(state_images, list) and state_images, "invalid_state_images", "Inspection state has no images.")
    verify_fingerprints(state_images)

    attempts = state.get("generation_attempts")
    require(
        isinstance(attempts, int) and 0 <= attempts <= 2,
        "invalid_generation_attempts",
        "Inspection state has an invalid generation attempt count.",
    )
    require(
        attempts < 2,
        "correction_limit_reached",
        "The one-pass correction limit has already been reached.",
    )

    request = load_json(Path(args.request).expanduser().resolve())
    require(
        request.get("contract") == RUNNER_CONTRACT,
        "invalid_runner_contract",
        f"Request contract must be {RUNNER_CONTRACT}.",
    )
    require(
        request.get("correction") is None,
        "manual_correction_not_allowed",
        "The standalone runner derives its one allowed correction from pixel-grounded output inspection.",
    )

    stored_plan = state.get("creative_plan")
    if attempts > 0 and isinstance(stored_plan, dict):
        plan = stored_plan
    else:
        plan = build_creative_plan(state, request)
    prompt = state.get("compiled_prompt") if attempts > 0 else None
    if not isinstance(prompt, str) or len(prompt.strip()) < 40:
        prompt = compile_generation_prompt(plan)
    references = normalize_reference_images(request, state_images, plan_reference_roles(plan))
    canvas = normalize_canvas(request, plan["canvas"]["aspect_ratio"])
    output = normalize_output(request)

    generation_capabilities = request_capabilities(
        args.generation_adapter,
        args.generation_adapter_arg,
        GENERATION_CONTRACT,
        args.timeout,
    )
    operations = generation_capabilities.get("operations")
    require(
        generation_capabilities.get("reference_conditioned_generation") is True,
        "reference_generation_unavailable",
        REFERENCE_GENERATION_FAILURE,
    )
    require(
        isinstance(operations, list) and "multi_image_composite" in operations,
        "generation_operation_unavailable",
        REFERENCE_GENERATION_FAILURE,
    )
    inspection_capabilities = request_capabilities(
        args.inspection_adapter,
        args.inspection_adapter_arg,
        INSPECTION_CONTRACT,
        args.timeout,
    )
    purposes = inspection_capabilities.get("purposes")
    require(
        inspection_capabilities.get("pixel_inspection") is True,
        "output_inspection_unavailable",
        PIXEL_INSPECTION_FAILURE,
    )
    require(
        isinstance(purposes, list) and "output_quality_gate" in purposes,
        "output_inspection_unavailable",
        PIXEL_INSPECTION_FAILURE,
    )

    required_ids = {image["id"] for image in state_images if image.get("must_use") is True}
    selected_ids = set(plan_reference_roles(plan))
    state["creative_plan"] = plan
    state["compiled_prompt"] = prompt
    correction: Optional[Dict[str, str]] = None
    previous_image: Optional[Dict[str, str]] = None
    if attempts == 1:
        stored_correction = state.get("pending_correction")
        if isinstance(stored_correction, dict):
            correction = normalize_correction(stored_correction)
        elif isinstance(state.get("last_quality_gate"), dict):
            correction = derive_targeted_correction(state["last_quality_gate"], plan)
        previous = state.get("last_generated_image")
        if isinstance(previous, dict):
            previous_image = previous

    while attempts < 2:
        if correction is not None:
            require(
                generation_capabilities.get("targeted_correction") is True,
                "targeted_correction_unavailable",
                "Generation backend cannot apply the one allowed targeted correction.",
            )

        generation_request: Dict[str, Any] = {
            "contract": GENERATION_CONTRACT,
            "operation": "multi_image_composite",
            "prompt": prompt.strip(),
            "reference_images": references,
            "canvas": canvas,
            "output": output,
        }
        if correction is not None:
            generation_request["correction"] = correction
            if previous_image is not None:
                generation_request["previous_image"] = previous_image
        if isinstance(request.get("provider_options"), dict):
            generation_request["provider_options"] = request["provider_options"]

        generation_response = invoke_adapter(
            args.generation_adapter,
            args.generation_adapter_arg,
            generation_request,
            args.timeout,
        )
        generated_image = validate_generated_image(generation_response, required_ids)
        used_ids = sorted(set(generation_response["used_reference_images"]))

        quality_request: Dict[str, Any] = {
            "contract": INSPECTION_CONTRACT,
            "operation": "inspect_images",
            "purpose": "output_quality_gate",
            "images": [
                {
                    "id": image["id"],
                    "source": image["source"],
                    "source_type": image["source_type"],
                    "must_use": image["must_use"],
                    "role": plan_reference_roles(plan).get(image["id"], "source_reference"),
                }
                for image in state_images
                if image["id"] in selected_ids
            ]
            + [image_locator_as_inspection_input(generated_image)],
            "analysis_scope": OUTPUT_ANALYSIS_SCOPE,
            "quality_requirements": quality_requirements(plan),
        }
        quality_response = invoke_adapter(
            args.inspection_adapter,
            args.inspection_adapter_arg,
            quality_request,
            args.timeout,
        )
        quality = validate_quality_response(quality_response)

        attempts += 1
        state["reference_conditioned_generation"] = "PASS"
        state["generation_reference_handles"] = used_ids
        state["generation_attempts"] = attempts
        state["last_generated_image"] = generated_image
        state["last_quality_gate"] = quality
        state["updated_at"] = utc_now()

        if quality["passed"]:
            state.pop("pending_correction", None)
            write_json_atomic(state_path, state)
            success_result = {
                "contract": RUNNER_CONTRACT,
                "status": "success",
                "pixel_inspection": "PASS",
                "reference_conditioned_generation": "PASS",
                "inspected_image_handles": state["inspected_image_handles"],
                "generation_reference_handles": used_ids,
                "generation_attempt": attempts,
                "image": generated_image,
                "quality_gate": quality,
                "creative_summary": {
                    "canvas_aspect_ratio": plan["canvas"]["aspect_ratio"],
                    "primary_style": STYLE_FAMILIES[plan["primary_style"]]["label"],
                    "supporting_style": (
                        STYLE_FAMILIES[plan["supporting_style"]]["label"] if plan.get("supporting_style") else None
                    ),
                    "future_premise": plan["future_premise"],
                    "spatial_stage": plan["spatial_stage"],
                    "material_system": plan["material_system"],
                    "emotional_tension": plan["emotional_tension"],
                },
            }
            write_json_atomic(result_path, success_result)
            return {"status": "success", "result": str(result_path), "image": generated_image}

        correction = quality["targeted_correction"] or derive_targeted_correction(quality, plan)
        state["pending_correction"] = correction
        previous_image = generated_image
        write_json_atomic(state_path, state)
        if attempts >= 2:
            failed_result = {
                "contract": RUNNER_CONTRACT,
                "status": "quality_failed",
                "generation_attempt": attempts,
                "image": generated_image,
                "failures": quality["failures"],
                "applied_correction": correction,
            }
            write_json_atomic(result_path, failed_result)
            raise RunnerError(
                "quality_gate_failed",
                "Generated output still failed after the one allowed targeted correction.",
                {"result": str(result_path), "generation_attempt": attempts},
            )

    raise RunnerError("generation_exhausted", "No generation attempt remains.")


def cmd_plan(args: argparse.Namespace) -> Dict[str, Any]:
    state = load_json(Path(args.state).expanduser().resolve())
    require(state.get("contract") == RUNNER_CONTRACT, "invalid_state_contract", "Inspection state contract is invalid.")
    require(state.get("pixel_inspection") == "PASS", "pixel_inspection_not_passed", PIXEL_INSPECTION_FAILURE)
    state_images = state.get("images")
    require(isinstance(state_images, list) and state_images, "invalid_state_images", "Inspection state has no images.")
    verify_fingerprints(state_images)
    request = load_json(Path(args.request).expanduser().resolve())
    require(
        request.get("contract") == RUNNER_CONTRACT,
        "invalid_runner_contract",
        f"Request contract must be {RUNNER_CONTRACT}.",
    )
    plan = build_creative_plan(state, request)
    output_value = {
        "contract": RUNNER_CONTRACT,
        "creative_plan": plan,
        "compiled_prompt": compile_generation_prompt(plan),
        "reference_roles": plan_reference_roles(plan),
    }
    output_path = Path(args.output).expanduser().resolve()
    write_json_atomic(output_path, output_value)
    return {"status": "plan_compiled", "output": str(output_path)}


def cmd_protocol(_: argparse.Namespace) -> Dict[str, Any]:
    return {
        "runner_contract": RUNNER_CONTRACT,
        "inspection_contract": INSPECTION_CONTRACT,
        "generation_contract": GENERATION_CONTRACT,
        "workflow": [
            "inspect all source pixels",
            "build the Asset Board and compile the creative plan",
            "generate with every must-use image as an actual visual reference",
            "inspect the rendered output",
            "apply at most one pixel-grounded targeted correction",
        ],
        "inspection_request_example": {
            "contract": RUNNER_CONTRACT,
            "images": [
                {"id": "image-01", "source": "path-or-handle", "source_type": "path", "must_use": True}
            ],
        },
        "generation_request_example": {
            "contract": RUNNER_CONTRACT,
            "brief": "Create a source-faithful Y2K collage poster.",
            "style": "auto",
            "supporting_style": None,
            "canvas": {"aspect_ratio": "2:3"},
            "text": {"headline": "EXACT OPTIONAL TEXT", "micro_labels": ["READY"]},
            "output": {"format": "png"},
        },
        "optional_generation_fields": {
            "brief": "User direction. The aliases request and prompt are also accepted as direction, not as a final compiled prompt.",
            "style": ["auto"] + STYLE_ORDER,
            "supporting_style": "An approved, non-competing family that contributes one pair-specific subsystem.",
            "hero_image_id": "Optional inspected image id explicitly designated as the central Hero; must_use alone never implies Hero.",
            "cohero_image_id": "Optional inspected image id explicitly designated as a shared Co-hero.",
            "canvas": "Omit to let the runner select a source-responsive ratio.",
            "text": "Exact string or an object with headline and up to three micro_labels.",
            "allow_authored_text": "Optional boolean. Omit for source-density-aware automatic text; false forbids authored text; true permits one short route-specific phrase.",
            "reference_images": "Omit to include every must-use source automatically; entries may override planned roles.",
            "provider_options": "Optional adapter-owned object; the runner does not depend on it.",
        },
        "supporting_style_pairs": [
            {
                "primary": primary,
                "supporting": supporting,
                "purpose": rule["purpose"],
                "subsystem": rule["subsystem"],
                "visible_grammar": "roughly 20–35%",
            }
            for (primary, supporting), rule in SUPPORTING_PAIR_RULES.items()
        ],
        "adapter_transport": {
            "mechanism": "local executable receiving one JSON object on stdin and returning one JSON object on stdout",
            "authentication": "owned by the adapter or host environment; never placed in runner requests",
            "inspection_capabilities": {
                "contract": INSPECTION_CONTRACT,
                "operation": "capabilities",
                "expected": {
                    "pixel_inspection": True,
                    "purposes": ["source_asset_board", "output_quality_gate"],
                },
            },
            "generation_capabilities": {
                "contract": GENERATION_CONTRACT,
                "operation": "capabilities",
                "expected": {
                    "reference_conditioned_generation": True,
                    "targeted_correction": True,
                    "operations": ["multi_image_composite"],
                },
            },
        },
    }


def add_adapter_arguments(parser: argparse.ArgumentParser, name: str) -> None:
    parser.add_argument(
        f"--{name}-adapter",
        required=True,
        help=f"Executable implementing the {name} JSON adapter contract.",
    )
    parser.add_argument(
        f"--{name}-adapter-arg",
        action="append",
        default=[],
        help=f"Argument passed directly to the {name} adapter; repeat as needed.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Standalone, vendor-neutral Y2K collage planner and fail-closed image runner.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    protocol_parser = subparsers.add_parser(
        "protocol",
        help="Print the runner request format and adapter contracts as JSON.",
    )
    protocol_parser.set_defaults(handler=cmd_protocol)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect all source images and write a fingerprinted PASS state.",
    )
    inspect_parser.add_argument("--request", required=True, help="Path to the source inspection request JSON.")
    inspect_parser.add_argument("--state", required=True, help="New state JSON path; it must not already exist.")
    inspect_parser.add_argument(
        "--adapter",
        required=True,
        help="Executable implementing the inspection JSON adapter contract.",
    )
    inspect_parser.add_argument(
        "--adapter-arg",
        action="append",
        default=[],
        help="Argument passed directly to the adapter; repeat as needed.",
    )
    inspect_parser.add_argument("--timeout", type=int, default=300, help="Adapter timeout in seconds.")
    inspect_parser.set_defaults(handler=cmd_inspect)

    plan_parser = subparsers.add_parser(
        "plan",
        help="Build the Asset Board and compiled prompt without generating an image.",
    )
    plan_parser.add_argument("--state", required=True, help="PASS state created by the inspect phase.")
    plan_parser.add_argument("--request", required=True, help="Path to the creative request JSON.")
    plan_parser.add_argument("--output", required=True, help="Path for the creative plan and compiled prompt JSON.")
    plan_parser.set_defaults(handler=cmd_plan)

    generate_parser = subparsers.add_parser(
        "generate",
        help="Verify reference input, generate, and run output quality inspection.",
    )
    generate_parser.add_argument("--state", required=True, help="PASS state created by the inspect phase.")
    generate_parser.add_argument("--request", required=True, help="Path to the generation request JSON.")
    generate_parser.add_argument("--result", required=True, help="Path for the structured result JSON.")
    add_adapter_arguments(generate_parser, "generation")
    add_adapter_arguments(generate_parser, "inspection")
    generate_parser.add_argument("--timeout", type=int, default=600, help="Adapter timeout in seconds.")
    generate_parser.set_defaults(handler=cmd_generate)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if hasattr(args, "timeout"):
            require(args.timeout > 0, "invalid_timeout", "Timeout must be a positive integer.")
        result = args.handler(args)
    except RunnerError as exc:
        error: Dict[str, Any] = {
            "status": "error",
            "code": exc.code,
            "message": exc.message,
        }
        if exc.details:
            error["details"] = exc.details
        print(json.dumps(error, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
