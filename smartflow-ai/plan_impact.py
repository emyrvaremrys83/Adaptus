"""Show the effect of duration estimates separately from sequencing effects."""
import streamlit as st


def render_impact_summary(outcomes, use_ai, language):
    tr = language == "Türkçe"

    def label(turkish, english):
        return turkish if tr else english

    st.markdown("#### " + label("AI süreleri planı nasıl değiştiriyor?", "How do AI durations affect the plan?"))
    st.caption(label(
        "Aynı işler, öncelik kuralı ve başlangıç zamanı karşılaştırılıyor. Yalnızca işlem süreleri değişiyor; sonuçlar simülasyon modelinin tahminidir.",
        "Same jobs, priority rule and start time. Only processing durations change; results are estimates from a simulation-trained model."))
    if outcomes.empty:
        st.info(label("Karşılaştırmak için bir iş ekle veya demo seç.", "Add a job or select a demo to compare."))
        return
    original_finish = outcomes["Original finish"].max()
    ai_finish = outcomes["AI finish"].max()
    shift = (ai_finish - original_finish).total_seconds() / 3600
    original_late = int((outcomes["Original delay (h)"] > 0).sum())
    ai_late = int((outcomes["AI delay (h)"] > 0).sum())
    a, b, c, d = st.columns(4)
    a.metric(label("Bitiş · girilen süreler", "Finish · original estimates"), original_finish.strftime("%d/%m %H:%M"))
    b.metric(label("Bitiş · AI süreleri", "Finish · AI estimates"), ai_finish.strftime("%d/%m %H:%M"),
             f"{shift:+.2f} h", delta_color="inverse")
    c.metric(label("Geciken iş · girilen süreler", "Late jobs · original estimates"), str(original_late))
    d.metric(label("Geciken iş · AI süreleri", "Late jobs · AI estimates"), str(ai_late),
             f"{ai_late - original_late:+d}", delta_color="inverse")
    newly_late = int(outcomes["Newly late"].sum())
    if newly_late:
        st.warning(label(
            f"AI süreleriyle {newly_late} iş daha teslim tarihini aşıyor. Ayrıntıları aşağıdaki teslim tablosunda görebilirsin.",
            f"With AI durations, {newly_late} additional jobs miss their deadlines. See the delivery table below."))


def render_delivery_table(outcomes, use_ai, language):
    tr = language == "Türkçe"

    def label(turkish, english):
        return turkish if tr else english

    st.markdown("#### " + label("Teslim tarihleri · öncelik planı", "Delivery deadlines · priority plan"))
    if outcomes.empty:
        st.info(label("Planda iş yok.", "No jobs in the plan."))
        return
    active_delay = "AI delay (h)" if use_ai else "Original delay (h)"
    late_only = st.checkbox(label("Yalnızca aktif planda geciken işleri göster", "Show only late jobs in the active plan"),
                            value=True, key="show_late_jobs_only")
    rows = outcomes.copy()
    rows = rows.sort_values([active_delay, "Due at"], ascending=[False, True])
    if late_only:
        rows = rows[rows[active_delay] > 0]
    if rows.empty:
        st.success(label("Aktif öncelik planında geciken iş yok.", "No late jobs in the active priority plan."))
        return

    late = label("Gecikiyor", "Late")
    newly_late = label("Yeni gecikme (AI)", "Newly late (AI)")
    on_time = label("Zamanında", "On time")
    status_col = label("Aktif plan durumu", "Active plan status")
    table = rows[["Job", "Due at", "Original finish", "AI finish", "Original delay (h)", "AI delay (h)"]].copy()
    table[status_col] = [
        newly_late if use_ai and row["Newly late"] else late if row[active_delay] > 0 else on_time
        for row in rows.to_dict("records")
    ]
    names = {
        "Due at": label("Teslim hedefi", "Due at"),
        "Original finish": label("Bitiş · girilen", "Finish · original"),
        "AI finish": label("Bitiş · AI", "Finish · AI"),
        "Original delay (h)": label("Gecikme · girilen (sa)", "Delay · original (h)"),
        "AI delay (h)": label("Gecikme · AI (sa)", "Delay · AI (h)"),
    }
    for column in ("Due at", "Original finish", "AI finish"):
        table[column] = table[column].dt.strftime("%d/%m/%Y %H:%M")
    table = table.rename(columns=names)

    def color_status(row):
        color = "#fff0d6" if row[status_col] == newly_late else "#fee2e2" if row[status_col] == late else "#ecfdf5"
        return [f"background-color: {color}; color: #172033"] * len(row)

    st.dataframe(table.style.apply(color_status, axis=1), hide_index=True, width="stretch",
                 column_config={names[column]: st.column_config.NumberColumn(format="%.2f")
                                for column in ("Original delay (h)", "AI delay (h)")})
    st.caption(label(
        "Kırmızı: geciken iş · Turuncu: yalnızca AI süreleriyle geciken iş · Yeşil: zamanında. Gecikme, planlanan bitişin teslim hedefini aştığı süredir.",
        "Red: late · Amber: late only with AI durations · Green: on time. Delay is the amount by which planned finish exceeds the deadline."))
