"""การคำนวณออกแบบหน้าตัดคาน คสล. สี่เหลี่ยมผืนผ้า (วิธีกำลัง, ACI 318 / วสท.)

หน่วยที่ใช้ภายใน: kg, cm  (กำลังวัสดุเป็น ksc = kg/cm²)
"""

from dataclasses import dataclass, field
from math import ceil, floor, pi, sqrt

ES = 2.04e6  # ksc, โมดูลัสยืดหยุ่นเหล็กเสริม
EPS_CU = 0.003  # ความเครียดสูงสุดของคอนกรีต

# ขนาดเหล็กเสริม (มม.)
BAR_SIZES = {
    "RB6": 6, "RB9": 9, "DB10": 10, "DB12": 12, "DB16": 16,
    "DB20": 20, "DB25": 25, "DB28": 28, "DB32": 32,
}


def bar_area(dia_mm: float) -> float:
    """พื้นที่หน้าตัดเหล็ก 1 เส้น (cm²)"""
    return pi * (dia_mm / 10) ** 2 / 4


def beta1(fc: float) -> float:
    """ค่า β1 ของบล็อกหน่วยแรงอัด (fc ใน ksc)"""
    if fc <= 280:
        return 0.85
    return max(0.65, 0.85 - 0.05 * (fc - 280) / 70)


def phi_flexure(eps_t: float, fy: float) -> float:
    """ตัวคูณลดกำลังดัดตามความเครียดเหล็กรับแรงดึง"""
    eps_y = fy / ES
    if eps_t >= 0.005:
        return 0.90
    if eps_t <= eps_y:
        return 0.65
    return 0.65 + 0.25 * (eps_t - eps_y) / (0.005 - eps_y)


@dataclass
class BeamInput:
    b: float  # cm
    h: float  # cm
    cover: float  # cm ระยะหุ้มถึงผิวเหล็กปลอก
    fc: float  # ksc
    fy: float  # ksc เหล็กยืน
    fyt: float  # ksc เหล็กปลอก
    Mu: float  # tf-m
    Vu: float  # tf
    main_bar: str = "DB20"
    stirrup_bar: str = "RB9"
    stirrup_legs: int = 2
    agg_size: float = 2.0  # cm ขนาดมวลรวมโตสุด


@dataclass
class FlexureResult:
    d: float
    Rn: float
    rho_req: float
    rho_min: float
    rho_max: float
    As_req: float
    n_bars: int
    As_prov: float
    n_per_layer: int
    a: float
    c: float
    eps_t: float
    phi: float
    phiMn: float  # tf-m
    ok: bool
    messages: list = field(default_factory=list)


@dataclass
class ShearResult:
    Vc: float  # tf
    phiVc: float  # tf
    Vs_req: float  # tf
    Av: float  # cm²
    s_req: float | None  # cm (None = ไม่ต้องการเหล็กปลอกด้วยกำลัง)
    s_max: float  # cm
    s_use: float  # cm
    phiVn: float  # tf
    ok: bool
    messages: list = field(default_factory=list)


def effective_depth(inp: BeamInput) -> float:
    db = BAR_SIZES[inp.main_bar] / 10
    ds = BAR_SIZES[inp.stirrup_bar] / 10
    return inp.h - inp.cover - ds - db / 2


def bars_per_layer(inp: BeamInput) -> int:
    """จำนวนเหล็กสูงสุดที่วางได้ใน 1 ชั้น"""
    db = BAR_SIZES[inp.main_bar] / 10
    ds = BAR_SIZES[inp.stirrup_bar] / 10
    clear = max(2.5, db, 4 / 3 * inp.agg_size)  # ระยะช่องว่างน้อยสุดระหว่างเหล็ก
    width = inp.b - 2 * (inp.cover + ds)
    return max(0, floor((width + clear) / (db + clear)))


def design_flexure(inp: BeamInput) -> FlexureResult:
    fc, fy, b = inp.fc, inp.fy, inp.b
    d = effective_depth(inp)
    Mu = inp.Mu * 1e5  # tf-m -> kg-cm
    msgs = []

    rho_min = max(0.8 * sqrt(fc) / fy, 14 / fy)
    b1 = beta1(fc)
    # ρ ที่ทำให้ εt = 0.005 (tension-controlled)
    rho_max = 0.85 * b1 * fc / fy * EPS_CU / (EPS_CU + 0.005)

    Rn = Mu / (0.9 * b * d**2)
    disc = 1 - 2 * Rn / (0.85 * fc)
    if disc < 0:
        rho_req = float("nan")
        msgs.append("หน้าตัดเล็กเกินไป ไม่สามารถรับโมเมนต์ได้ด้วยเหล็กเสริมรับแรงดึงอย่างเดียว — ให้เพิ่มขนาดหน้าตัด")
    else:
        rho_req = 0.85 * fc / fy * (1 - sqrt(disc))

    if rho_req == rho_req and rho_req > rho_max:
        msgs.append("ρ ที่ต้องการเกิน ρmax (εt < 0.005) — ควรเพิ่มขนาดหน้าตัดหรือออกแบบเป็นคานเสริมเหล็กรับแรงอัด")

    rho_design = rho_req if rho_req == rho_req else rho_max
    rho_design = max(rho_design, rho_min)
    As_req = rho_design * b * d

    Ab = bar_area(BAR_SIZES[inp.main_bar])
    n_bars = max(2, ceil(As_req / Ab - 1e-9))
    As_prov = n_bars * Ab
    n_layer = bars_per_layer(inp)
    if n_layer < 2:
        msgs.append("ความกว้างคานไม่พอสำหรับวางเหล็กอย่างน้อย 2 เส้น")
    elif n_bars > n_layer:
        msgs.append(f"เหล็ก {n_bars} เส้นวางได้ไม่พอใน 1 ชั้น (สูงสุด {n_layer} เส้น/ชั้น) — ต้องวาง 2 ชั้น หรือใช้เหล็กขนาดใหญ่ขึ้น")

    # ตรวจสอบกำลังของหน้าตัดที่เลือกใช้
    a = As_prov * fy / (0.85 * fc * b)
    c = a / b1
    eps_t = EPS_CU * (d - c) / c
    phi = phi_flexure(eps_t, fy)
    phiMn = phi * As_prov * fy * (d - a / 2) / 1e5

    if eps_t < 0.004:
        msgs.append(f"εt = {eps_t:.4f} < 0.004 ไม่เป็นไปตามข้อกำหนดความเหนียวของคาน")

    ok = phiMn >= inp.Mu and eps_t >= 0.004 and 2 <= n_layer and n_bars <= n_layer
    return FlexureResult(d, Rn, rho_req, rho_min, rho_max, As_req, n_bars, As_prov,
                         n_layer, a, c, eps_t, phi, phiMn, ok, msgs)


def design_shear(inp: BeamInput) -> ShearResult:
    fc, b, fyt = inp.fc, inp.b, inp.fyt
    d = effective_depth(inp)
    Vu = inp.Vu * 1000  # tf -> kg
    phi = 0.75
    msgs = []

    Vc = 0.53 * sqrt(fc) * b * d
    Av = inp.stirrup_legs * bar_area(BAR_SIZES[inp.stirrup_bar])
    Vs_req = max(0.0, Vu / phi - Vc)
    Vs_limit = 2.1 * sqrt(fc) * b * d

    ok = True
    if Vs_req > Vs_limit:
        ok = False
        msgs.append("Vs ที่ต้องการเกิน 2.1√fc' b d — ต้องเพิ่มขนาดหน้าตัด")

    # ระยะเรียงสูงสุด
    if Vs_req > 1.1 * sqrt(fc) * b * d:
        s_max = min(d / 4, 30)
    else:
        s_max = min(d / 2, 60)
    # เหล็กปลอกน้อยสุด Av,min
    s_max = min(s_max, Av * fyt / (0.2 * sqrt(fc) * b), Av * fyt / (3.5 * b))

    s_req = Av * fyt * d / Vs_req if Vs_req > 0 else None
    if Vu <= 0.5 * phi * Vc:
        msgs.append("Vu ≤ φVc/2 ตามทฤษฎีไม่ต้องใช้เหล็กปลอก (แนะนำให้ใส่เหล็กปลอกน้อยสุด)")
    elif Vs_req == 0:
        msgs.append("Vu ≤ φVc ใช้เหล็กปลอกน้อยสุด")

    s_use = min(s_max, s_req) if s_req else s_max
    s_use = floor(s_use * 2) / 2  # ปัดลงทีละ 0.5 cm
    if s_use < 5:
        ok = False
        msgs.append("ระยะเรียงเหล็กปลอกน้อยเกินไป — ให้เพิ่มขนาด/จำนวนขาเหล็กปลอก หรือขยายหน้าตัด")

    phiVn = phi * (Vc + Av * fyt * d / s_use) if s_use > 0 else phi * Vc
    ok = ok and phiVn >= Vu
    return ShearResult(Vc / 1000, phi * Vc / 1000, Vs_req / 1000, Av, s_req, s_max,
                       s_use, phiVn / 1000, ok, msgs)
