import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle
import streamlit as st

from beam_calc import BAR_SIZES, BeamInput, beta1, design_flexure, design_shear, effective_depth

st.set_page_config(page_title="ออกแบบหน้าตัดคาน คสล.", page_icon="🏗️", layout="wide")
st.title("🏗️ ออกแบบหน้าตัดคาน คสล. (Rectangular Beam)")
st.caption("วิธีกำลัง (Strength Design) ตาม ACI 318 / วสท. — หน่วย kg, cm, ksc, tf")

main_bars = [k for k in BAR_SIZES if k.startswith("DB")]
stirrups = ["RB6", "RB9", "DB10", "DB12"]

with st.sidebar:
    st.header("ข้อมูลหน้าตัด")
    b = st.number_input("ความกว้าง b (cm)", 10.0, 200.0, 25.0, 5.0)
    h = st.number_input("ความลึก h (cm)", 15.0, 300.0, 50.0, 5.0)
    cover = st.number_input("ระยะหุ้มคอนกรีต (cm)", 1.5, 10.0, 3.0, 0.5)

    st.header("วัสดุ")
    fc = st.number_input("fc' คอนกรีต (ksc)", 150.0, 700.0, 240.0, 10.0)
    fy = st.selectbox("fy เหล็กยืน (ksc)", [3000, 4000, 5000], index=1,
                      format_func=lambda v: {3000: "SD30 (3000)", 4000: "SD40 (4000)", 5000: "SD50 (5000)"}[v])
    fyt = st.selectbox("fyt เหล็กปลอก (ksc)", [2400, 3000, 4000], index=0,
                       format_func=lambda v: {2400: "SR24 (2400)", 3000: "SD30 (3000)", 4000: "SD40 (4000)"}[v])

    st.header("เหล็กเสริม")
    main_bar = st.selectbox("เหล็กเสริมหลัก", main_bars, index=main_bars.index("DB20"))
    stirrup_bar = st.selectbox("เหล็กปลอก", stirrups, index=1)
    legs = st.number_input("จำนวนขาเหล็กปลอก", 2, 6, 2, 1)

    st.header("แรงภายในประลัย")
    Mu = st.number_input("Mu (tf-m)", 0.0, 1000.0, 15.0, 0.5)
    Vu = st.number_input("Vu (tf)", 0.0, 1000.0, 12.0, 0.5)

inp = BeamInput(b=b, h=h, cover=cover, fc=fc, fy=fy, fyt=fyt, Mu=Mu, Vu=Vu,
                main_bar=main_bar, stirrup_bar=stirrup_bar, stirrup_legs=int(legs))

if effective_depth(inp) <= 0:
    st.error("ความลึกหน้าตัดไม่พอสำหรับระยะหุ้มและเหล็กเสริม")
    st.stop()
flex = design_flexure(inp)
shear = design_shear(inp)


def draw_section():
    fig, ax = plt.subplots(figsize=(4, 4 * h / b if h / b < 2 else 8))
    ax.add_patch(Rectangle((0, 0), b, h, fc="#d9d9d9", ec="black", lw=1.5))
    ds = BAR_SIZES[stirrup_bar] / 10
    db = BAR_SIZES[main_bar] / 10
    ax.add_patch(FancyBboxPatch((cover + ds / 2, cover + ds / 2), b - 2 * cover - ds, h - 2 * cover - ds,
                                boxstyle=f"round,pad=0,rounding_size={2 * ds}", fc="none", ec="#1f4e79", lw=1.5))

    # เหล็กล่าง (รับแรงดึง) แบ่งชั้นตามจำนวนที่วางได้
    per_layer = max(2, flex.n_per_layer)
    remaining, layer = flex.n_bars, 0
    while remaining > 0:
        n = min(per_layer, remaining)
        if n == 1:
            n = 2 if remaining >= 2 else 1
        y = cover + ds + db / 2 + layer * (db + 2.5)
        x0, x1 = cover + ds + db / 2, b - cover - ds - db / 2
        xs = [x0 + i * (x1 - x0) / (n - 1) for i in range(n)] if n > 1 else [b / 2]
        for x in xs:
            ax.add_patch(Circle((x, y), db / 2, fc="#c00000", ec="black"))
        remaining -= n
        layer += 1

    # เหล็กบน (เหล็กยึดปลอก) 2 เส้น
    yt = h - cover - ds - db / 2
    for x in (cover + ds + db / 2, b - cover - ds - db / 2):
        ax.add_patch(Circle((x, yt), db / 2, fc="#7f7f7f", ec="black"))

    ax.annotate("", (0, -3), (b, -3), arrowprops=dict(arrowstyle="<->"))
    ax.text(b / 2, -6, f"b = {b:g} cm", ha="center", va="top")
    ax.annotate("", (b + 3, 0), (b + 3, h), arrowprops=dict(arrowstyle="<->"))
    ax.text(b + 5, h / 2, f"h = {h:g} cm", rotation=90, va="center")
    ax.set_xlim(-5, b + 12)
    ax.set_ylim(-12, h + 5)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig


def badge(ok: bool) -> str:
    return "✅ ผ่าน" if ok else "❌ ไม่ผ่าน"


col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("หน้าตัดคาน")
    st.pyplot(draw_section())
    st.markdown(
        f"**เหล็กล่าง:** {flex.n_bars}-{main_bar}  \n"
        f"**เหล็กบน:** 2-{main_bar} (ยึดปลอก)  \n"
        f"**เหล็กปลอก:** {stirrup_bar} @ {shear.s_use:g} cm ({int(legs)} ขา)"
    )

with col2:
    st.subheader(f"1) ออกแบบรับโมเมนต์ดัด — {badge(flex.ok)}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Mu (tf-m)", f"{Mu:.2f}")
    m2.metric("φMn (tf-m)", f"{flex.phiMn:.2f}")
    m3.metric("อัตราส่วน Mu/φMn", f"{Mu / flex.phiMn:.2f}" if flex.phiMn else "-")
    for m in flex.messages:
        st.warning(m)
    with st.expander("รายการคำนวณโมเมนต์", expanded=True):
        st.markdown(f"""
| รายการ | ค่า |
|---|---|
| ความลึกประสิทธิผล d | {flex.d:.2f} cm |
| β₁ | {beta1(fc):.3f} |
| Rn = Mu / (φ b d²) | {flex.Rn:.2f} ksc |
| ρ ที่ต้องการ | {flex.rho_req:.5f} |
| ρmin = max(0.8√fc'/fy, 14/fy) | {flex.rho_min:.5f} |
| ρmax (εt = 0.005) | {flex.rho_max:.5f} |
| As ที่ต้องการ | {flex.As_req:.2f} cm² |
| As ที่ใช้ ({flex.n_bars}-{main_bar}) | {flex.As_prov:.2f} cm² |
| จำนวนเหล็กสูงสุดต่อชั้น | {flex.n_per_layer} เส้น |
| a = As fy / (0.85 fc' b) | {flex.a:.2f} cm |
| c = a / β₁ | {flex.c:.2f} cm |
| εt | {flex.eps_t:.4f} |
| φ | {flex.phi:.3f} |
| φMn = φ As fy (d − a/2) | {flex.phiMn:.2f} tf-m |
""")

    st.subheader(f"2) ออกแบบรับแรงเฉือน — {badge(shear.ok)}")
    v1, v2, v3 = st.columns(3)
    v1.metric("Vu (tf)", f"{Vu:.2f}")
    v2.metric("φVn (tf)", f"{shear.phiVn:.2f}")
    v3.metric("ระยะเรียงเหล็กปลอก (cm)", f"{shear.s_use:g}")
    for m in shear.messages:
        (st.info if shear.ok else st.warning)(m)
    with st.expander("รายการคำนวณแรงเฉือน", expanded=True):
        s_req = f"{shear.s_req:.1f} cm" if shear.s_req else "-"
        st.markdown(f"""
| รายการ | ค่า |
|---|---|
| Vc = 0.53√fc' b d | {shear.Vc:.2f} tf |
| φVc (φ = 0.75) | {shear.phiVc:.2f} tf |
| Vs ที่ต้องการ = Vu/φ − Vc | {shear.Vs_req:.2f} tf |
| Av ({int(legs)} ขา {stirrup_bar}) | {shear.Av:.3f} cm² |
| s ที่ต้องการ = Av fyt d / Vs | {s_req} |
| s สูงสุด (ข้อกำหนด + Av,min) | {shear.s_max:.1f} cm |
| s ที่ใช้ | {shear.s_use:g} cm |
| φVn = φ(Vc + Av fyt d / s) | {shear.phiVn:.2f} tf |
""")

st.divider()
st.caption("⚠️ โปรแกรมนี้ใช้เพื่อการศึกษาและออกแบบเบื้องต้น ผลการออกแบบควรได้รับการตรวจสอบโดยวิศวกรผู้มีใบอนุญาต")
