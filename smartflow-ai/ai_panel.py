"""Bilingual Streamlit panel for the local duration prediction demo."""
import pandas as pd
import plotly.express as px
import streamlit as st

from ai_predictor import OPERATIONS, PROCESS, SETUP, predict_hours, train_demo_model


def render_impact_map(outcomes, language):
    """Visualize job finish shifts and let users inspect one job at a time."""
    tr = language == "Türkçe"

    def label(turkish, english):
        return turkish if tr else english

    st.markdown("#### " + label("AI etki haritası", "AI impact map"))
    st.caption(label(
        "Öncelik planındaki her çubuk, işin AI süreleri kullanıldığında kaç saat daha geç veya erken bittiğini gösterir. Kuyrukta bekleme de bu farka dahildir.",
        "Each bar shows how many hours later or earlier a job finishes in the priority plan with AI durations. Waiting in the machine queue is included."))
    if outcomes is None:
        st.info(label("Plan etkisi şu anda hesaplanamıyor.", "Schedule impact is currently unavailable."))
        return
    if outcomes.empty:
        st.info(label("Etki haritası için bir iş ekle veya demo seç.", "Add a job or select a demo to view the impact map."))
        return

    filters = {
        "all": label("Tüm işler", "All jobs"),
        "new": label("Yeni gecikenler", "Newly late"),
        "late": label("AI planında gecikenler", "Late with AI"),
    }
    selected_filter = st.radio(label("Haritada göster", "Show on map"), list(filters),
                               format_func=filters.get, horizontal=True, key="ai_impact_filter")
    rows = outcomes.copy()
    if selected_filter == "new":
        rows = rows[rows["Newly late"]]
    elif selected_filter == "late":
        rows = rows[rows["AI delay (h)"] > 0]
    if rows.empty:
        st.info(label("Bu filtrede iş yok. ‘Tüm işler’ seçeneğine dön.",
                      "No jobs match this filter. Select 'All jobs' to return."))
        return

    on_time = label("Zamanında", "On time")
    already_late = label("Önceden gecikiyordu", "Already late")
    newly_late = label("Yeni gecikme", "Newly late")
    rows["Status"] = [
        newly_late if row["Newly late"] else already_late if row["AI delay (h)"] > 0 else on_time
        for row in rows.to_dict("records")
    ]
    rows = rows.sort_values("Finish shift (h)", ascending=False)
    rows["Due"] = rows["Due at"].dt.strftime("%d %b %H:%M")
    rows["Before"] = rows["Original finish"].dt.strftime("%d %b %H:%M")
    rows["After"] = rows["AI finish"].dt.strftime("%d %b %H:%M")
    shift_title = label("Bitiş kayması (saat)", "Finish shift (hours)")
    component_title = label("Parça", "Component")
    due_title = label("Teslim hedefi", "Deadline")
    before_title = label("Bitiş · girilen", "Finish · original")
    after_title = label("Bitiş · AI", "Finish · AI")
    chart_data = rows.rename(columns={"Component": component_title, "Due": due_title,
                                      "Before": before_title, "After": after_title})
    fig = px.bar(
        chart_data, x="Finish shift (h)", y="Job", orientation="h", color="Status",
        text="Finish shift (h)", category_orders={"Job": rows["Job"].tolist()},
        color_discrete_map={on_time: "#1a9c83", already_late: "#f0a64a", newly_late: "#d74359"},
        labels={"Finish shift (h)": shift_title, "Status": label("Teslim durumu", "Delivery status")},
        hover_data={component_title: True, due_title: True, before_title: True, after_title: True,
                    "Finish shift (h)": ":+.2f", "Status": False},
    )
    fig.update_traces(texttemplate="%{x:+.1f} sa" if tr else "%{x:+.1f} h",
                      textposition="outside", cliponaxis=False)
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(zeroline=True, zerolinecolor="#8892a6", gridcolor="rgba(128,128,128,.15)")
    fig.update_layout(height=max(390, 110 + len(rows) * 33), margin=dict(l=10, r=60, t=30, b=35),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      legend_title=None, bargap=.23)
    st.plotly_chart(fig, width="stretch", key="ai-impact-map",
                    config={"displayModeBar": False, "responsive": True})
    st.caption(label(
        "Yeşil: zamanında · Turuncu: girilen sürelerle de gecikiyordu · Kırmızı: AI süreleriyle yeni gecikme. Bu bir tahmindir.",
        "Green: on time · Amber: already late with original estimates · Red: newly late with AI durations. These are predictions."))

    visible_ids = rows["Job"].tolist()
    if st.session_state.get("ai_impact_job") not in visible_ids:
        st.session_state.ai_impact_job = visible_ids[0]
    st.markdown("#### " + label("Bir işi yakından incele", "Inspect a job"))
    selected_job = st.selectbox(label("İş seç", "Select job"), visible_ids,
                                format_func=lambda job_id: f"{job_id} · {rows.loc[rows['Job'] == job_id, 'Component'].iloc[0]}",
                                key="ai_impact_job")
    job = rows.loc[rows["Job"] == selected_job].iloc[0]
    st.caption(str(job["Component"]))
    a, b, c, d = st.columns(4)
    a.metric(label("Bitiş · girilen süre", "Finish · original"), job["Original finish"].strftime("%d/%m %H:%M"))
    b.metric(label("Bitiş · AI süresi", "Finish · AI"), job["AI finish"].strftime("%d/%m %H:%M"),
             f"{job['Finish shift (h)']:+.2f} h", delta_color="inverse")
    c.metric(label("Teslim hedefi", "Deadline"), job["Due at"].strftime("%d/%m %H:%M"))
    d.metric(label("AI planında gecikme", "Delay with AI"), f"{job['AI delay (h)']:.2f} h",
             f"{job['AI delay (h)'] - job['Original delay (h)']:+.2f} h", delta_color="inverse")
    if job["Newly late"]:
        st.warning(label("Bu iş, AI süreleriyle ilk kez teslim hedefini aşıyor.",
                         "This job first misses its deadline with AI durations."))
    elif job["AI delay (h)"] > 0:
        st.warning(label("Bu iş iki süre senaryosunda da teslim hedefini aşıyor.",
                         "This job misses its deadline in both duration scenarios."))
    else:
        st.success(label("Bu iş AI süreleriyle de teslim hedefinden önce bitiyor.",
                         "This job still finishes by its deadline with AI durations."))


def render_ai_panel(jobs, language, use_ai=False, outcomes=None):
    tr = language == "Türkçe"

    def label(turkish, english):
        return turkish if tr else english

    st.subheader(label("AI işlem süresi tahmini", "AI processing-time estimates"))
    st.info(label(
        "Bu yerel model simülasyon verileriyle eğitilmiştir. Gerçek fabrika doğruluğu ölçülmemiştir. Sayfanın üstündeki ‘AI süreleriyle planla’ anahtarı tahminleri plana uygular; kayıtlı süreler korunur.",
        "This local model is trained on synthetic data. Real-factory accuracy has not been measured. The 'Plan with AI durations' switch at the top applies predictions to the schedule; stored estimates are preserved."))
    st.caption(label(
        "AI planlama açık. Bitiş ve gecikme karşılaştırması Plan karşılaştırması sekmesinde." if use_ai else
        "AI planlama kapalı. Tahminleri Gantt grafiğinde denemek için üstteki anahtarı aç.",
        "AI planning is on. Finish and lateness comparisons are in Plan comparison." if use_ai else
        "AI planning is off. Turn on the switch above to try these estimates in the Gantt charts."))
    try:
        with st.spinner(label("Yerel model hazırlanıyor…", "Preparing local model…")):
            _, report = train_demo_model()
        render_impact_map(outcomes, language)
        st.divider()
        names = {"Torna": "Turning", "Freze": "Milling", "Delik": "Drilling", "Montaj": "Assembly", "Paketleme": "Packaging"}
        st.markdown("#### " + label("Seçili işlerin tahminleri", "Predictions for current jobs"))
        st.caption(label("Sol paneldeki 1 / 2 / 3 seçenekleri hem planı hem bu tabloyu günceller.",
                         "The sidebar's 1 / 2 / 3 buttons update both the plan and this table."))
        if jobs.empty:
            st.info(label("Henüz kayıtlı iş yok.", "No saved jobs yet."))
        else:
            predictions = predict_hours(jobs)
            table = pd.DataFrame({
                "Job": jobs["Job"].to_numpy(),
                label("Operasyon", "Operation"): jobs["Operasyon"].map(lambda op: op if tr else names[op]).to_numpy(),
                label("Girilen süre (saat)", "Original estimate (h)"): jobs[PROCESS].to_numpy(dtype=float),
                label("AI tahmini (saat)", "AI estimate (h)"): predictions.round(2),
                label("Fark (saat)", "Difference (h)"): (predictions - jobs[PROCESS].to_numpy(dtype=float)).round(2),
            })
            st.dataframe(table, hide_index=True, width="stretch")
        with st.expander(label("Ayrıntılar ve elle deneme", "Details and manual inputs")):
            a, b = st.columns(2)
            a.metric(label("Modelin ortalama mutlak hatası", "Model mean absolute error"), f"{report['model_mae']:.2f} h")
            b.metric(label("Girilen sürelerin ortalama mutlak hatası", "Original estimates' mean absolute error"), f"{report['baseline_mae']:.2f} h")
            st.caption(label(
                f"Yalnızca simülasyon testi: {report['training_rows']} eğitim, {report['test_rows']} ayrı test kaydı. Hata, tahmin ile simüle edilen işlem süresi arasındaki ortalama mutlak farktır.",
                f"Synthetic evaluation only: {report['training_rows']} training and {report['test_rows']} held-out test records. Error is the average absolute difference from simulated processing time."))

            st.markdown("#### " + label("Kendi örneğini dene", "Try an example"))
            names = {"Torna": "Turning", "Freze": "Milling", "Delik": "Drilling", "Montaj": "Assembly", "Paketleme": "Packaging"}
            a, b, c = st.columns(3)
            operation = a.selectbox(label("Operasyon", "Operation"), OPERATIONS,
                                   format_func=lambda op: op if tr else names[op], key="ai_operation")
            duration = b.number_input(label("Girilen işlem süresi (saat)", "Estimated processing time (h)"), .5, 48., 4., .5, key="ai_duration")
            setup = c.number_input(label("Hazırlık süresi (saat)", "Setup time (h)"), 0., 12., .5, .1, key="ai_setup")
            sample = pd.DataFrame({"Operasyon": [operation], PROCESS: [duration], SETUP: [setup]})
            estimate = float(predict_hours(sample)[0])
            st.metric(label("AI işlem süresi tahmini", "AI processing-time estimate"), f"{estimate:.2f} h",
                      f"{estimate - duration:+.2f} h", delta_color="off")
            st.caption(label("Tahmin yalnızca işlem süresidir; hazırlık süresi buna dahil değildir.",
                             "Prediction covers processing only; setup time is not included."))

        with st.expander(label("Model nasıl çalışıyor?", "How does the model work?")):
            st.write(label(
                "regresyon modeli operasyon, girilen işlem süresi ve hazırlık süresinden süre çarpanını öğrenir. 2.400 örnek üretim kaydı sabit rastgele tohumla oluşturulur; %75'i eğitim, %25'i test için ayrılır. Simülasyonda operasyonlara göre farklı yavaşlama ve rastgele sapmalar varsayılır. Bunlar gerçek üretim bulguları değildir. Makine etkisi ayrıca öğrenilmez; mevcut uygulamada her operasyonun tek uygun makinesi vardır. Kurulumdan sonra API, internet veya GPU gerekmez.",
                "A regression model learns a duration multiplier from operation, estimated processing time and setup time. We generate 2,400 reproducible synthetic runs, splitting 75% for training and 25% for testing. Operation-specific slowdowns and random variation are simulator assumptions, not factory findings. Machine effects are not learned separately because each operation currently has one eligible machine. After installation, no API, internet or GPU is needed."))
    except (ValueError, OSError) as error:
        st.error(label("AI tahmini oluşturulamadı: ", "Could not generate AI estimates: ") + str(error))
