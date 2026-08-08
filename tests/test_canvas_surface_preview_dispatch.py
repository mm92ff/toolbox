import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from app import constants
from app.canvas import surface_render as surface_render_module
from app.canvas.toolbox_canvas import CanvasSurface
from app.domain.models import ToolboxEntry
from app.services.media_thumbnails import MEDIA_KIND_IMAGE, MEDIA_KIND_VIDEO, MediaThumbnailService


def _ensure_app() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _base_entry(path: str, entry_id: str) -> ToolboxEntry:
    return ToolboxEntry(
        title=entry_id,
        kind=constants.ENTRY_KIND_TOOL,
        path=path,
        x=constants.CANVAS_PADDING,
        y=constants.CANVAS_PADDING,
        entry_id=entry_id,
    )


def test_image_preview_dispatch_does_not_forward_ffmpeg_manual_path(monkeypatch) -> None:
    _ensure_app()
    calls: dict[str, object] = {}

    monkeypatch.setattr(surface_render_module, "is_supported_image_path", lambda _path: True)
    monkeypatch.setattr(surface_render_module, "is_supported_video_path", lambda _path: False)

    def _fake_request(
        _self,
        source_path: str,
        kind: str,
        icon_size: int,
        mode: str,
        cache_dir,
        **kwargs,
    ) -> None:
        calls["source_path"] = source_path
        calls["kind"] = kind
        calls["icon_size"] = icon_size
        calls["mode"] = mode
        calls["kwargs"] = kwargs

    monkeypatch.setattr(MediaThumbnailService, "request", _fake_request)

    surface = CanvasSurface()
    entries = [_base_entry(r"C:\Images\sample.png", "img-1")]
    surface.set_entries(
        entries=entries,
        icon_provider=QtWidgets.QFileIconProvider(),
        icon_size=constants.DEFAULT_ICON_SIZE,
        tile_frame_enabled=constants.DEFAULT_TILE_FRAME_ENABLED,
        tile_frame_thickness=constants.DEFAULT_TILE_FRAME_THICKNESS,
        tile_frame_color=constants.DEFAULT_TILE_FRAME_COLOR,
        tile_highlight_color=constants.DEFAULT_TILE_HIGHLIGHT_COLOR,
        grid_spacing_x=constants.DEFAULT_GRID_SPACING_X,
        grid_spacing_y=constants.DEFAULT_GRID_SPACING_Y,
        auto_compact_left=constants.DEFAULT_AUTO_COMPACT_LEFT,
        section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
        section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
        section_gap=constants.DEFAULT_SECTION_PROTECTED_GAP,
        section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
        selected_entry_ids=set(),
        hidden_entry_ids=set(),
        viewport_width=1200,
        image_file_preview_enabled=True,
        video_file_preview_enabled=True,
        ffmpeg_manual_path=r"C:\ffmpeg\ffmpeg.exe",
    )

    assert calls["source_path"] == r"C:\Images\sample.png"
    assert calls["kind"] == MEDIA_KIND_IMAGE
    assert calls["icon_size"] == constants.DEFAULT_ICON_SIZE
    assert calls["mode"] == constants.DEFAULT_IMAGE_FILE_PREVIEW_MODE
    assert "manual_ffmpeg_path" not in calls["kwargs"]


def test_video_preview_dispatch_forwards_manual_ffmpeg_path(monkeypatch) -> None:
    _ensure_app()
    calls: dict[str, object] = {}

    monkeypatch.setattr(surface_render_module, "is_supported_image_path", lambda _path: False)
    monkeypatch.setattr(surface_render_module, "is_supported_video_path", lambda _path: True)

    def _fake_request(
        _self,
        source_path: str,
        kind: str,
        icon_size: int,
        mode: str,
        cache_dir,
        **kwargs,
    ) -> None:
        calls["source_path"] = source_path
        calls["kind"] = kind
        calls["icon_size"] = icon_size
        calls["mode"] = mode
        calls["manual_ffmpeg_path"] = kwargs.get("manual_ffmpeg_path")

    monkeypatch.setattr(MediaThumbnailService, "request", _fake_request)

    surface = CanvasSurface()
    entries = [_base_entry(r"C:\Videos\clip.mp4", "vid-1")]
    surface.set_entries(
        entries=entries,
        icon_provider=QtWidgets.QFileIconProvider(),
        icon_size=constants.DEFAULT_ICON_SIZE,
        tile_frame_enabled=constants.DEFAULT_TILE_FRAME_ENABLED,
        tile_frame_thickness=constants.DEFAULT_TILE_FRAME_THICKNESS,
        tile_frame_color=constants.DEFAULT_TILE_FRAME_COLOR,
        tile_highlight_color=constants.DEFAULT_TILE_HIGHLIGHT_COLOR,
        grid_spacing_x=constants.DEFAULT_GRID_SPACING_X,
        grid_spacing_y=constants.DEFAULT_GRID_SPACING_Y,
        auto_compact_left=constants.DEFAULT_AUTO_COMPACT_LEFT,
        section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
        section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
        section_gap=constants.DEFAULT_SECTION_PROTECTED_GAP,
        section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
        selected_entry_ids=set(),
        hidden_entry_ids=set(),
        viewport_width=1200,
        image_file_preview_enabled=True,
        video_file_preview_enabled=True,
        ffmpeg_manual_path=r"C:\ffmpeg\ffmpeg.exe",
    )

    assert calls["source_path"] == r"C:\Videos\clip.mp4"
    assert calls["kind"] == MEDIA_KIND_VIDEO
    assert calls["icon_size"] == constants.DEFAULT_ICON_SIZE
    assert calls["mode"] == constants.DEFAULT_IMAGE_FILE_PREVIEW_MODE
    assert calls["manual_ffmpeg_path"] == r"C:\ffmpeg\ffmpeg.exe"
