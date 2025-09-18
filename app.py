# app.py —  IoT (single-file, web-only)
import io
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from dataclasses import dataclass
 
st.set_page_config(page_title="Protocolos IoT", page_icon="📡", layout="wide")
st.title("📡 Sesión 3 · Comparativa de Protocolos IoT (WiFi, Zigbee, LoRaWAN, NB-IoT)")
st.caption("Grado en Ingeniería Informática · Blockchain y IoT · Práctica 100% web")
 
# ---------- Modelo en un archivo ----------
@dataclass
class ProtocolParams:
    name: str
    bitrate_bps: float
    tx_current_mA: float
    rx_current_mA: float
    idle_current_mA: float
    range_m: float
    overhead_bytes: int
    base_latency_ms: float
    duty_cycle_limit: float
    notes: str = ""
 
def default_protocols():
    return [
        ProtocolParams("WiFi",    10e6, 180.0, 50.0, 5.0,     30,   80,  50,   1.0,  "alto throughput"),
        ProtocolParams("Zigbee",  250e3, 35.0,  19.0, 0.3,    100,  25,  100,  1.0,  "malla, bajo consumo"),
        ProtocolParams("LoRaWAN", 5e3,   45.0,  12.0, 0.01,   15000,20,  800,  0.01, "largo alcance, bajo bitrate"),
        ProtocolParams("NB-IoT",  26e3,  220.0, 30.0, 0.05,   10000,30,  200,  1.0,  "cobertura celular"),
    ]
 
def scenario(n_sensors:int, msgs_per_day:int, payload_bytes:int, rx_ratio:float):
    return dict(n_sensors=n_sensors, msgs_per_day=msgs_per_day,
                payload_bytes=payload_bytes, rx_ratio=rx_ratio)
 
def estimate(proto: ProtocolParams, sc: dict, battery_mAh: float, header_factor: float=1.0):
    msgs = sc["msgs_per_day"]; payload = sc["payload_bytes"]; rx_ratio = sc["rx_ratio"]
    bytes_total = payload + int(proto.overhead_bytes * header_factor)
    bits_total = bytes_total * 8
    tx_time_s = bits_total / proto.bitrate_bps
    rx_time_s = tx_time_s * rx_ratio
    if proto.duty_cycle_limit < 1.0:
        tx_time_s = tx_time_s / proto.duty_cycle_limit
    tx_total_h = (tx_time_s * msgs) / 3600.0
    rx_total_h = (rx_time_s * msgs) / 3600.0
    active_h = tx_total_h + rx_total_h
    idle_h = max(0.0, 24.0 - active_h)
    tx_mAh = proto.tx_current_mA * tx_total_h
    rx_mAh = proto.rx_current_mA * rx_total_h
    idle_mAh = proto.idle_current_mA * idle_h
    daily_mAh_per_sensor = tx_mAh + rx_mAh + idle_mAh
    latency_ms = proto.base_latency_ms + (tx_time_s * 1000.0)
    days_battery = battery_mAh / daily_mAh_per_sensor if daily_mAh_per_sensor > 0 else np.inf
    return {
        "protocol": proto.name,
        "consumo_mAh_dia": daily_mAh_per_sensor,
        "latencia_ms": latency_ms,
        "cobertura_m": proto.range_m,
        "dias_bateria": days_battery,
        "notas": proto.notes
    }
 
def evaluate_all(protocols, sc, battery_mAh, header_factor):
    rows = [estimate(p, sc, battery_mAh, header_factor) for p in protocols]
    df = pd.DataFrame(rows)
    return df.sort_values(by="consumo_mAh_dia").reset_index(drop=True)
 
# ---------- UI ----------
with st.sidebar:
    st.header("🎚️ Parámetros del escenario")
    c1, c2 = st.columns(2)
    n_sensors = c1.number_input("Nº sensores", 1, 10000, 100, step=10)
    msgs_per_day = c2.number_input("Mensajes por día", 1, 10000, 24, step=1)
    payload_bytes = st.slider("Payload (bytes)", 1, 1024, 50, step=1)
    rx_ratio = st.slider("Ratio downlink (0–1)", 0.0, 1.0, 0.1, step=0.05)
    battery_mAh = st.number_input("Batería por sensor (mAh)", 10, 20000, 2400, step=100)
    header_factor = st.slider("Factor de overhead (1=nominal)", 0.5, 3.0, 1.0, step=0.1)
    st.caption("Tip: exporta el CSV al final.")
 
protocols = default_protocols()
sc = scenario(n_sensors, msgs_per_day, payload_bytes, rx_ratio)
df = evaluate_all(protocols, sc, battery_mAh, header_factor)
 
st.subheader("📊 Resultados comparativos")
st.dataframe(df, use_container_width=True)
 
st.markdown("### 🔌 Consumo energético (mAh/día)")
fig1, ax1 = plt.subplots()
ax1.bar(df["protocol"], df["consumo_mAh_dia"])
ax1.set_ylabel("mAh/día (menor es mejor)")
st.pyplot(fig1, clear_figure=True)
 
st.markdown("### ⏱️ Latencia media estimada (ms)")
fig2, ax2 = plt.subplots()
ax2.bar(df["protocol"], df["latencia_ms"])
ax2.set_ylabel("ms (menor es mejor)")
st.pyplot(fig2, clear_figure=True)
 
st.markdown("### 📡 Cobertura típica (m)")
fig3, ax3 = plt.subplots()
ax3.bar(df["protocol"], df["cobertura_m"])
ax3.set_ylabel("metros (mayor es mejor)")
st.pyplot(fig3, clear_figure=True)
 
st.markdown("### 🔋 Vida de batería estimada (días)")
fig4, ax4 = plt.subplots()
ax4.bar(df["protocol"], df["dias_bateria"])
ax4.set_ylabel("días (mayor es mejor)")
st.pyplot(fig4, clear_figure=True)
 
best_energy = df.iloc[df["consumo_mAh_dia"].idxmin()]["protocol"]
best_coverage = df.iloc[df["cobertura_m"].idxmax()]["protocol"]
best_latency = df.iloc[df["latencia_ms"].idxmin()]["protocol"]
st.info(f"**Resumen** · Consumo mínimo: **{best_energy}** · Mejor cobertura: **{best_coverage}** · Menor latencia: **{best_latency}**.")
 
st.markdown("---")
st.subheader("📤 Exportar resultados")
csv_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button("Descargar CSV", data=csv_bytes, file_name="resultados_protocolos.csv", mime="text/csv")
 
with st.expander("🧩 Caso aplicado (debatir y justificar)"):
    st.markdown("""
**Elige y defiende un protocolo:**
1) Smart Home → *Zigbee vs WiFi*  
2) Parking urbano → *NB-IoT vs LoRaWAN*  
3) Riego agrícola → *LoRaWAN vs NB-IoT*
 
Escribe una justificación corta (2–3 frases) con datos de arriba.
""")
    just = st.text_area("Justificación del equipo", height=120, placeholder="Nuestro caso es... elegimos ... porque ...")
    if st.button("Guardar justificación"):
        st.session_state["justificacion"] = just
        st.success("Justificación guardada en la sesión (cópiala a tu portafolio).")
 
st.caption("Modelo docente y simplificado. Ajusta parámetros para explorar compromisos reales.")
