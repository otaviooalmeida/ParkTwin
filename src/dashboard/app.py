import json
import sys
from pathlib import Path
from typing import Any

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from twin.repository import TwinRepository  # noqa: E402


DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "parktwin.db"
DEFAULT_OUTPUTS_DIR = PROJECT_ROOT / "data" / "outputs"


def main() -> None:
    st.set_page_config(page_title="ParkTwin Dashboard", layout="wide")
    st.title("ParkTwin")

    db_path, outputs_dir, event_limit = _render_sidebar()

    snapshot = _load_latest_snapshot(db_path, outputs_dir)
    history = _load_occupancy_history(db_path, outputs_dir)
    events = _load_recent_events(db_path, outputs_dir, event_limit)
    latest_image_path = _find_latest_annotated_image(outputs_dir)

    if snapshot is None:
        st.info("Nenhum estado encontrado. Rode o pipeline para gerar snapshots.")
        return

    _render_metrics(snapshot)

    image_column, table_column = st.columns([2, 1])
    with image_column:
        st.subheader("Imagem anotada mais recente")
        if latest_image_path is None:
            st.warning("Nenhuma imagem anotada encontrada.")
        else:
            st.image(str(latest_image_path), use_container_width=True)
            st.caption(str(latest_image_path.relative_to(PROJECT_ROOT)))

    with table_column:
        st.subheader("Estado atual das vagas")
        st.dataframe(
            _spot_rows(snapshot["spots"]),
            hide_index=True,
            use_container_width=True,
        )

    st.subheader("Histórico de ocupação")
    if history:
        st.line_chart(
            {
                "occupied": [item["occupied_count"] for item in history],
                "free": [item["free_count"] for item in history],
                "uncertain": [item["uncertain_count"] for item in history],
            }
        )
        st.dataframe(history, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum histórico disponível.")

    st.subheader("Últimos eventos por vaga")
    if events:
        st.dataframe(events, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum evento disponível.")


def _render_sidebar() -> tuple[Path, Path, int]:
    st.sidebar.header("Fonte de dados")
    db_path = Path(
        st.sidebar.text_input("SQLite DB", value=str(DEFAULT_DB_PATH))
    )
    outputs_dir = Path(
        st.sidebar.text_input("Diretório de outputs", value=str(DEFAULT_OUTPUTS_DIR))
    )
    event_limit = st.sidebar.number_input(
        "Eventos recentes",
        min_value=1,
        max_value=500,
        value=100,
        step=10,
    )
    st.sidebar.caption("O dashboard usa SQLite quando há snapshots. Caso contrário, lê os JSONs em data/outputs.")
    return db_path, outputs_dir, int(event_limit)


def _render_metrics(snapshot: dict[str, Any]) -> None:
    occupied_count = snapshot["occupied_count"]
    total_spots = snapshot["total_spots"]
    occupancy_rate = snapshot["occupancy_rate"] * 100

    columns = st.columns(5)
    columns[0].metric("Total", total_spots)
    columns[1].metric("Ocupadas", occupied_count)
    columns[2].metric("Livres", snapshot["free_count"])
    columns[3].metric("Incertas", snapshot["uncertain_count"])
    columns[4].metric("Ocupação", f"{occupancy_rate:.1f}%")

    st.caption(f"Última atualização: {snapshot['timestamp']}")


def _load_latest_snapshot(db_path: Path, outputs_dir: Path) -> dict[str, Any] | None:
    if db_path.exists():
        snapshot = TwinRepository(db_path).get_latest_snapshot()
        if snapshot is not None:
            return {
                "timestamp": snapshot.timestamp,
                "parking_lot_id": snapshot.parking_lot_id,
                "spots": [spot.__dict__ for spot in snapshot.spots],
                "total_spots": snapshot.total_spots,
                "occupied_count": snapshot.occupied_count,
                "free_count": snapshot.free_count,
                "uncertain_count": snapshot.uncertain_count,
                "occupancy_rate": snapshot.occupancy_rate,
            }

    latest_state_path = _find_latest_state_file(outputs_dir)
    if latest_state_path is None:
        return None

    return _load_state_json(latest_state_path)


def _load_occupancy_history(db_path: Path, outputs_dir: Path) -> list[dict[str, Any]]:
    if db_path.exists():
        history = TwinRepository(db_path).get_occupancy_history()
        if history:
            return history

    return [
        _history_row_from_state(_load_state_json(path))
        for path in sorted(outputs_dir.glob("*_state.json"), key=lambda item: item.stat().st_mtime)
    ]


def _load_recent_events(
    db_path: Path,
    outputs_dir: Path,
    limit: int,
) -> list[dict[str, Any]]:
    if db_path.exists():
        events = TwinRepository(db_path).get_recent_events(limit)
        if events:
            return events

    latest_state_path = _find_latest_state_file(outputs_dir)
    if latest_state_path is None:
        return []

    state = _load_state_json(latest_state_path)
    rows = [
        {
            "snapshot_timestamp": state["timestamp"],
            "spot_id": spot["id"],
            "status": spot["status"],
            "confidence": spot.get("confidence"),
            "created_at": state["timestamp"],
        }
        for spot in state["spots"]
    ]
    return rows[:limit]


def _load_state_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    data.setdefault("parking_lot_id", None)
    data.setdefault("occupancy_rate", _calculate_occupancy_rate(data))
    return data


def _calculate_occupancy_rate(state: dict[str, Any]) -> float:
    total_spots = state.get("total_spots", 0)
    if total_spots == 0:
        return 0.0

    return state.get("occupied_count", 0) / total_spots


def _history_row_from_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": state["timestamp"],
        "total_spots": state["total_spots"],
        "occupied_count": state["occupied_count"],
        "free_count": state["free_count"],
        "uncertain_count": state["uncertain_count"],
        "occupancy_rate": state["occupancy_rate"],
    }


def _spot_rows(spots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "spot_id": spot["id"],
            "status": spot["status"],
            "confidence": spot.get("confidence"),
            "occupied_since": spot.get("occupied_since"),
            "last_changed_at": spot.get("last_changed_at"),
        }
        for spot in spots
    ]


def _find_latest_state_file(outputs_dir: Path) -> Path | None:
    return _find_latest_file(outputs_dir, "*_state.json")


def _find_latest_annotated_image(outputs_dir: Path) -> Path | None:
    return _find_latest_file(outputs_dir, "*_annotated.jpg")


def _find_latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None

    files = list(directory.glob(pattern))
    if not files:
        return None

    return max(files, key=lambda item: item.stat().st_mtime)


if __name__ == "__main__":
    main()
