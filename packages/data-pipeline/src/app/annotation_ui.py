from __future__ import annotations

import os
from html import escape
from pathlib import Path
from typing import Any, Literal

import streamlit as st

from app.annotation_workspace import AnnotationKind, AnnotationValidationError, AnnotationWorkspace
from app.annotation_translation import TranslationHelperError


Kind = Literal["skills", "roles", "dedup"]
KIND_LABELS: dict[Kind, str] = {
    "skills": "技能",
    "roles": "岗位类别",
    "dedup": "重复岗位",
}


def _workspace() -> AnnotationWorkspace:
    repository_root = Path(__file__).resolve().parents[4]
    root = Path(
        os.environ.get("SKILLWORTH_ANNOTATION_ROOT", repository_root / "data/benchmarks")
    )
    silver_value = os.environ.get("SKILLWORTH_ANNOTATION_SILVER")
    return AnnotationWorkspace(
        benchmark_root=root,
        skill_taxonomy_path=Path(
            os.environ.get(
                "SKILLWORTH_SKILL_TAXONOMY", repository_root / "data/taxonomy/skills.yml"
            )
        ),
        role_taxonomy_path=Path(
            os.environ.get(
                "SKILLWORTH_ROLE_TAXONOMY",
                repository_root / "data/reference/role_taxonomy.v1.json",
            )
        ),
        silver_path=Path(silver_value) if silver_value else None,
    )


def _style() -> None:
    st.markdown(
        """
        <style>
        :root { --ink:#e8e4dc; --muted:#96938c; --line:#2a2b2d; --accent:#d6ff5f; }
        .stApp { background:#111214; color:var(--ink); }
        .block-container { max-width:1180px; padding-top:2.2rem; }
        h1,h2,h3 { letter-spacing:-.035em; }
        [data-testid="stMetric"] { background:transparent; border-top:1px solid var(--line); padding-top:.8rem; }
        [data-testid="stMetricLabel"] { text-transform:uppercase; letter-spacing:.12em; color:var(--muted); }
        .prediction { border-left:2px solid #d3a23a; padding:.7rem 1rem; color:#d4d0c8; background:#171719; }
        .prediction strong { color:#d3a23a; font-size:.72rem; letter-spacing:.12em; }
        .sample-meta { color:var(--muted); font:12px ui-monospace,SFMono-Regular,Consolas,monospace; letter-spacing:.06em; }
        .diff { color:#f1c16f; }
        .same { color:#8d918a; }
        [data-testid="stSidebar"] { border-right:1px solid var(--line); background:#151618; }
        .stButton button:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _goto(workspace: AnnotationWorkspace, kind: Kind, sample_id: str) -> None:
    workspace.remember_position(kind, sample_id)
    st.session_state["kind"] = kind
    st.session_state["sample_id"] = sample_id


def _landing(workspace: AnnotationWorkspace) -> None:
    st.title("Gold Benchmark 人工标注")
    st.caption("系统预测仅供参考，不会自动成为 Gold；所有 Gold 都需要人工明确确认。")
    progress = workspace.progress()
    columns = st.columns(4)
    for column, key, label in zip(
        columns[:3], ("skills", "roles", "dedup"), ("技能", "岗位类别", "重复岗位")
    ):
        item = progress[key]
        column.metric(label, f"{item.completed} / {item.total}")
    total_completed = sum(item.completed for item in progress.values())
    total = sum(item.total for item in progress.values())
    columns[3].metric("总进度", f"{total_completed} / {total}")
    st.progress(
        total_completed / total if total else 0,
        text=f"已人工确认 {total_completed} 条 · 剩余 {total - total_completed} 条",
    )

    st.subheader("继续标注")
    actions = st.columns(3)
    for column, kind in zip(actions, ("skills", "roles", "dedup")):
        sample_id = workspace.resume_sample_id(kind)
        if column.button(
            f"继续标注{KIND_LABELS[kind]}",
            key=f"continue_{kind}",
            width="stretch",
            disabled=sample_id is None,
        ) and sample_id:
            _goto(workspace, kind, sample_id)
            st.rerun()


def _sidebar(workspace: AnnotationWorkspace, kind: Kind, sample_id: str) -> str:
    with st.sidebar:
        st.markdown("### 标注会话")
        annotator = st.text_input("标注人", key="annotator", placeholder="请输入姓名或缩写")
        samples = workspace.pending_samples(kind)
        labels = {
            item["sample_id"]: f"{'✓' if item['completed'] else '○'} {index + 1:03d} · {item['sample_id']}"
            for index, item in enumerate(samples)
        }
        selected = st.selectbox(
            "跳转到样本",
            options=[item["sample_id"] for item in samples],
            index=next(index for index, item in enumerate(samples) if item["sample_id"] == sample_id),
            format_func=labels.get,
            key=f"jump_{kind}_{sample_id}",
        )
        if selected != sample_id:
            _goto(workspace, kind, selected)
            st.rerun()
        completed = [item["sample_id"] for item in samples if item["completed"]]
        with st.expander(f"已完成样本 · {len(completed)}"):
            st.write("\n".join(completed) if completed else "暂无已完成样本")
        st.markdown(
            "**快捷键**  \n"
            "`Ctrl/Cmd+Enter` 保存并下一条  \n"
            "`Alt+←` 上一条  ·  `Alt+→` 跳过  \n"
            "`Alt+A` 切换边界/不确定状态  \n"
            + ("`1` 同一岗位  ·  `2` 不同岗位" if kind == "dedup" else "")
        )
        if st.button("返回总览", key="back_overview", width="stretch"):
            st.session_state.pop("kind", None)
            st.session_state.pop("sample_id", None)
            st.rerun()
        return annotator


def _navigation(workspace: AnnotationWorkspace, kind: Kind, sample_id: str) -> None:
    ids = [item["sample_id"] for item in workspace.pending_samples(kind)]
    index = ids.index(sample_id)
    previous, skip = st.columns(2)
    if previous.button(
        "← 上一条",
        key=f"previous_{kind}_{sample_id}",
        shortcut="Alt+Left",
        disabled=index == 0,
        width="stretch",
    ):
        _goto(workspace, kind, ids[index - 1])
        st.rerun()
    if skip.button(
        "跳过 →",
        key=f"skip_{kind}_{sample_id}",
        shortcut="Alt+Right",
        disabled=index == len(ids) - 1,
        width="stretch",
    ):
        _goto(workspace, kind, ids[index + 1])
        st.rerun()


def _advance(workspace: AnnotationWorkspace, kind: Kind, sample_id: str) -> None:
    next_sample = workspace.next_unannotated(kind)
    if next_sample is not None:
        _goto(workspace, kind, str(next_sample["sample_id"]))
        return
    ids = [item["sample_id"] for item in workspace.pending_samples(kind)]
    index = ids.index(sample_id)
    _goto(workspace, kind, ids[min(index + 1, len(ids) - 1)])


def _header(workspace: AnnotationWorkspace, kind: Kind, sample_id: str) -> dict[str, Any]:
    sample = workspace.presented_sample(kind, sample_id)
    progress = workspace.progress()[kind]
    st.caption(
        f"{KIND_LABELS[kind]} 人工标注  ·  "
        f"已确认 {progress.completed} / {progress.total}"
    )
    st.markdown(
        f'<div class="sample-meta">样本 ID · {escape(sample_id)}</div>',
        unsafe_allow_html=True,
    )
    return sample


def _prediction(value: object) -> None:
    rendered = ", ".join(value) if isinstance(value, list) else str(value)
    st.markdown(
        f'<div class="prediction"><strong>系统预测 · 仅供参考，不是 Gold</strong><br>{escape(rendered or "无系统预测")}</div>',
        unsafe_allow_html=True,
    )


def _bilingual_job_content(sample: dict[str, Any]) -> None:
    translation = sample.get("translation")
    st.markdown(f"**原始英文岗位标题：** {sample['title'] or '未提供'}")
    st.markdown("### 中文辅助阅读")
    st.caption("辅助翻译，仅用于阅读；Gold 判断仍基于原始岗位内容。")
    if translation:
        st.subheader(translation["title_zh"])
        st.text(translation["description_zh"])
    else:
        st.info("当前样本暂无经过 hash 校验的中文辅助翻译，请查看英文原文。")
    with st.expander("查看英文原文", expanded=translation is None):
        st.markdown(f"**原始岗位标题：** {sample['title'] or '未提供'}")
        st.text(sample["description"] or "未提供原始 JD")


def _common_fields(kind: Kind, sample_id: str, existing: dict[str, Any] | None) -> tuple[bool, str]:
    ambiguous_key = f"ambiguous_{kind}_{sample_id}"
    if ambiguous_key not in st.session_state:
        st.session_state[ambiguous_key] = bool(existing and existing.get("ambiguous"))
    if st.button(
        "切换边界/不确定状态",
        key=f"toggle_ambiguous_{kind}_{sample_id}",
        shortcut="Alt+A",
        type="tertiary",
    ):
        st.session_state[ambiguous_key] = not st.session_state[ambiguous_key]
    ambiguous = st.checkbox(
        "边界/不确定样本（后续需要复核）",
        key=ambiguous_key,
    )
    notes = st.text_area(
        "标注备注",
        value=str(existing.get("annotation_notes") or "") if existing else "",
        key=f"notes_{kind}_{sample_id}",
        placeholder="记录判断依据、不确定点或修改原因",
    )
    return ambiguous, notes


def _save_error(action: Any) -> bool:
    try:
        action()
        return True
    except AnnotationValidationError as error:
        st.error(str(error))
        return False


def _skill_page(workspace: AnnotationWorkspace, sample_id: str, annotator: str) -> None:
    sample = _header(workspace, "skills", sample_id)
    st.caption(f"数据来源 · {sample['source']}")
    _bilingual_job_content(sample)
    _prediction([workspace.skill_options.get(value, value) for value in sample["prediction"]])
    existing = workspace.annotation("skills", sample_id)
    selected = st.multiselect(
        "人工 Gold 技能",
        options=list(workspace.skill_options),
        default=list(existing.get("gold_skills") or []) if existing else [],
        format_func=workspace.skill_options.get,
        key=f"gold_skills_{sample_id}",
        placeholder="搜索技能名称或分类",
    )
    st.caption("若按标注指南确认原文中没有 taxonomy 技能，可以人工确认空列表。")
    ambiguous, notes = _common_fields("skills", sample_id, existing)
    if st.button(
        "保存并下一条",
        key=f"save_skills_{sample_id}",
        type="primary",
        shortcut="Mod+Enter",
        width="stretch",
    ) and _save_error(
        lambda: workspace.save_skill(
            sample_id,
            selected,
            annotator=annotator,
            ambiguous=ambiguous,
            notes=notes,
            human_confirmed=True,
        )
    ):
        _advance(workspace, "skills", sample_id)
        st.session_state["flash"] = "技能 Gold 已原子保存。"
        st.rerun()
    _navigation(workspace, "skills", sample_id)


def _role_page(workspace: AnnotationWorkspace, sample_id: str, annotator: str) -> None:
    sample = _header(workspace, "roles", sample_id)
    st.caption(f"数据来源 · {sample['source']}")
    _bilingual_job_content(sample)
    predicted_role = sample["prediction"]
    _prediction(
        f"{workspace.role_labels.get(predicted_role, predicted_role)} · {predicted_role}"
    )
    existing = workspace.annotation("roles", sample_id)
    default = existing.get("gold_role") if existing else None
    role = st.selectbox(
        "人工 Gold 岗位类别",
        options=list(workspace.role_options),
        index=list(workspace.role_options).index(default) if default in workspace.role_options else None,
        key=f"gold_role_{sample_id}",
        format_func=lambda value: f"{workspace.role_labels[value]} · {value}",
        placeholder="选择岗位类别",
    )
    ambiguous, notes = _common_fields("roles", sample_id, existing)
    if st.button(
        "保存并下一条",
        key=f"save_roles_{sample_id}",
        type="primary",
        shortcut="Mod+Enter",
        width="stretch",
    ):
        if role is None:
            st.error("必须选择人工 Gold 岗位类别。")
        elif _save_error(
            lambda: workspace.save_role(
                sample_id,
                role,
                annotator=annotator,
                ambiguous=ambiguous,
                notes=notes,
                human_confirmed=True,
            )
        ):
            _advance(workspace, "roles", sample_id)
            st.session_state["flash"] = "岗位类别 Gold 已原子保存。"
            st.rerun()
    _navigation(workspace, "roles", sample_id)


def _job_panel(
    title: str,
    job: dict[str, Any],
    different_fields: set[str],
    translation: dict[str, Any] | None,
    role_labels: dict[str, str],
) -> None:
    st.markdown(f"### {title}")
    st.caption("辅助翻译，仅用于阅读；Gold 判断仍基于原始岗位内容。")
    if translation:
        st.markdown(f"**中文辅助岗位标题：** {translation['title_zh']}")
        st.text(translation["description_zh"])
    else:
        st.info("暂无经过 hash 校验的中文辅助翻译。")
    field_labels = {
        "company": "公司",
        "title": "岗位名称",
        "role": "岗位类别",
        "city": "城市",
        "salary": "薪资",
        "posted_at": "发布时间",
        "source": "来源",
    }
    for field in ("company", "title", "role", "city", "salary", "posted_at", "source"):
        marker = "diff" if field in different_fields else "same"
        value = job.get(field)
        if field == "role" and value:
            value = f"{role_labels.get(str(value), str(value))} · {value}"
        st.markdown(
            f'<div class="{marker}"><small>{field_labels[field]}</small><br>{escape(str(value or "未提供"))}</div>',
            unsafe_allow_html=True,
        )
    with st.expander("查看英文原文", expanded=translation is None):
        st.markdown(f"**原始岗位标题：** {job.get('title') or '未提供'}")
        st.text(job.get("description") or "未提供原始 JD")


def _dedup_page(workspace: AnnotationWorkspace, sample_id: str, annotator: str) -> None:
    sample = _header(workspace, "dedup", sample_id)
    _prediction("同一岗位" if sample["prediction"] else "不同岗位")
    different_fields = set(sample["different_fields"])
    translation = sample.get("translation") or {}
    left, right = st.columns(2)
    with left:
        _job_panel(
            "岗位 A",
            sample["left"],
            different_fields,
            translation.get("left"),
            workspace.role_labels,
        )
    with right:
        _job_panel(
            "岗位 B",
            sample["right"],
            different_fields,
            translation.get("right"),
            workspace.role_labels,
        )
    existing = workspace.annotation("dedup", sample_id)
    default = existing.get("gold_duplicate") if existing else None
    label_key = f"gold_dedup_{sample_id}"
    choose_same, choose_different = st.columns(2)
    if choose_same.button(
        "1 · 同一岗位", key=f"dedup_same_{sample_id}", shortcut="1", width="stretch"
    ):
        st.session_state[label_key] = True
    if choose_different.button(
        "2 · 不同岗位", key=f"dedup_different_{sample_id}", shortcut="2", width="stretch"
    ):
        st.session_state[label_key] = False
    label = st.radio(
        "人工 Gold 重复岗位标签",
        options=[True, False],
        index=[True, False].index(default) if type(default) is bool else None,
        format_func=lambda value: "同一岗位" if value else "不同岗位",
        horizontal=True,
        key=label_key,
    )
    ambiguous, notes = _common_fields("dedup", sample_id, existing)
    if st.button(
        "保存并下一条",
        key=f"save_dedup_{sample_id}",
        type="primary",
        shortcut="Mod+Enter",
        width="stretch",
    ):
        if type(label) is not bool:
            st.error("必须选择“同一岗位”或“不同岗位”。")
        elif _save_error(
            lambda: workspace.save_dedup(
                sample_id,
                label,
                annotator=annotator,
                ambiguous=ambiguous,
                notes=notes,
                human_confirmed=True,
            )
        ):
            _advance(workspace, "dedup", sample_id)
            st.session_state["flash"] = "重复岗位 Gold 已原子保存。"
            st.rerun()
    _navigation(workspace, "dedup", sample_id)


def run_app() -> None:
    st.set_page_config(page_title="SkillWorth Gold 人工标注", page_icon="✓", layout="wide")
    _style()
    try:
        workspace = _workspace()
        flash = st.session_state.pop("flash", None)
        if flash:
            st.success(flash)
        kind = st.session_state.get("kind")
        if kind not in KIND_LABELS:
            _landing(workspace)
            return
        sample_id = st.session_state.get("sample_id") or workspace.resume_sample_id(kind)
        if sample_id is None:
            st.info(f"当前没有可用的{KIND_LABELS[kind]}样本。")
            return
        workspace.remember_position(kind, sample_id)
        annotator = _sidebar(workspace, kind, sample_id)
        if kind == "skills":
            _skill_page(workspace, sample_id, annotator)
        elif kind == "roles":
            _role_page(workspace, sample_id, annotator)
        else:
            _dedup_page(workspace, sample_id, annotator)
    except (FileNotFoundError, AnnotationValidationError, TranslationHelperError, KeyError) as error:
        st.error(f"标注工作区无法启动：{error}")


if __name__ == "__main__":
    run_app()
