import os
import re
import glob

_FLOAT = re.compile(r'^[+\-]?((\d+(\.\d*)?|\.\d+))([eE][+\-]?\d+)?$')

# ------------------- ayudantes -------------------
def _strip_comment(s: str) -> str:
    for mark in ('#', '!'):
        p = s.find(mark)
        if p != -1:
            s = s[:p]
    return s

def _norm_token(tok: str) -> str:
    t = tok.strip()
    t = re.sub(r'([0-9])([dD])([+\-]?\d+)$', r'\1E\3', t)
    if (',' in t) and ('.' not in t):
        t = t.replace(',', '.')
    return t

def float_number(line: str) -> bool:
    toks = line.strip().split()
    if not toks:
        return False
    return all(_FLOAT.match(t) and ('.' in t or 'e' in t.lower()) for t in toks)


# ------------------- lectura de datos -------------------
def leer_registros(ruta_archivo):
    V1, V2, HT, HB = [], [], [], []
    with open(ruta_archivo, "r", encoding="utf-8", errors="ignore") as f:
        lineas = f.readlines()

    i = 0
    while i < len(lineas) and not ("NO" in lineas[i] and "V1" in lineas[i] and "V2" in lineas[i] and "HT" in lineas[i] and "HB" in lineas[i]):
        i += 1
    if i == len(lineas):
        return {'V1': tuple(), 'V2': tuple(), 'HB': tuple(), 'HT': tuple()}

    j = i + 1
    if j < len(lineas) and "=" in lineas[j]:
        j += 1

    while j < len(lineas):
        s = _strip_comment(lineas[j]).strip()
        j += 1
        if not s:
            continue
        toks = s.split()
        if len(toks) < 5:
            continue
        try:
            v1 = float(_norm_token(toks[1]))
            v2 = float(_norm_token(toks[2]))
            ht = float(_norm_token(toks[3]))
            hb = float(_norm_token(toks[4]))
        except ValueError:
            continue

        V1.append(v1)
        V2.append(v2)
        HT.append(ht)
        HB.append(hb)

    return {'V1': tuple(V1), 'V2': tuple(V2), 'HB': tuple(HB), 'HT': tuple(HT)}


# ------------------- comparación numero a numero -------------------
def errores(a, b):
    abs_err = abs(a - b)
    if abs(a) < 1:
        rel_err = abs_err
    else:
        rel_err = abs_err / abs(a)

    return abs_err, rel_err

def compararaciones_numericas(tA, tB):
    V1a, V1b = tA.get('V1', ()), tB.get('V1', ())
    V2a, V2b = tA.get('V2', ()), tB.get('V2', ())
    HBa, HBb = tA.get('HB', ()), tB.get('HB', ())
    HTa, HTb = tA.get('HT', ()), tB.get('HT', ())

    n = min(len(V1a), len(V1b), len(V2a), len(V2b), len(HBa), len(HBb), len(HTa), len(HTb))
    out = []
    for i in range(n):
# Regla: si original == 0 -> err_rel = err_abs
        _, v1_rel = errores(V1a[i], V1b[i])
        _, v2_rel = errores(V2a[i], V2b[i])
        _, ht_rel = errores(HTa[i], HTb[i])
        _, hb_rel = errores(HBa[i], HBb[i])

        out.append({
            "idx": i+1,
            "V1_error_rel": v1_rel,
            "V2_error_rel": v2_rel,
            "HT_error_rel": ht_rel,
            "HB_error_rel": hb_rel,
        })
    return out


# ------------------- salida .txt de comparaciones -------------------
def formatear_txt_detalle(resultados):
    if not resultados:
        return "Sin datos\n"
# ancho de cada columna numérica
    W = 18
    header = (
        f"{'idx':>6}  "
        f"{'V1_error_rel':>{W}}  "
        f"{'V2_error_rel':>{W}}  "
        f"{'HB_error_rel':>{W}}  "
        f"{'HT_error_rel':>{W}}"
    )
    lineas = [header, "-" * len(header)]

    for r in resultados:
        lineas.append(
            f"{r['idx']:6d}  "
            f"{r['V1_error_rel']:{W}.6e}  "
            f"{r['V2_error_rel']:{W}.6e}  "
            f"{r['HB_error_rel']:{W}.6e}  "
            f"{r['HT_error_rel']:{W}.6e}"
        )
    return "\n".join(lineas) + "\n"


# ------------------- nombrado / búsqueda de archivos -------------------
# Acepta formatos "chuS2" y "chuS 2"
_NUM_CHUS = re.compile(r'chus\s*([0-9]+)\.plt$', re.IGNORECASE)

def buscar_variantes(carpeta, i):
    for nombre in (f"chuS{i}", f"chuS {i}"):
        ruta = os.path.join(carpeta, nombre)
        if os.path.exists(ruta):
            return ruta
    return None

def nombre_salida(nombre_plt):
    m = _NUM_CHUS.search(nombre_plt)
    if m:
        return f"comparacion_chuS{m.group(1)}.txt"
    base = os.path.splitext(os.path.basename(nombre_plt))[0].replace(' ', '_')
    return f"comparacion_{base}.txt"


# ------------------- comparaciones de carpetas -------------------
def comparar_carpeta_a_vs_b(carpeta_a, carpeta_b, carpeta_salida, cantidad=80):
    """
    Compara chuS 1..chuS {cantidad} de carpeta_a (ORIGINAL) vs carpeta_b (NUEVO).
    Genera un .txt por par con la tabla grande.
    """
    os.makedirs(carpeta_salida, exist_ok=True)
    generados = []
    for i in range(1, cantidad+1):
        ruta_a = buscar_variantes(carpeta_a, i)
        ruta_b = buscar_variantes(carpeta_b, i)
        if not ruta_a or not ruta_b:
            continue

        tuplas_A = leer_registros(ruta_a)  # {'V1','V2','HB','HT'}
        tuplas_B = leer_registros(ruta_b)  # {'V1','V2','HB','HT'}

        resultados = compararaciones_numericas(tuplas_A, tuplas_B)

        ruta_out = os.path.join(carpeta_salida, nombre_salida(os.path.basename(ruta_a)))
        with open(ruta_out, "w", encoding="utf-8") as f:
            f.write(formatear_txt_detalle(resultados))
        generados.append(ruta_out)

        print(f"[OK] {os.path.basename(ruta_a)} vs {os.path.basename(ruta_b)}  "
              f"nA={len(tuplas_A.get('HT', ()))}/{len(tuplas_A.get('HB', ()))}/{len(tuplas_A.get('V1', ()))}/{len(tuplas_A.get('V2', ()))}, "
              f"nB={len(tuplas_B.get('HT', ()))}/{len(tuplas_B.get('HB', ()))}/{len(tuplas_B.get('V1', ()))}/{len(tuplas_B.get('V2', ()))}, "
              f"comparados={len(resultados)}  -> {ruta_out}")
    return generados

COLUMNAS = ("V1_error_rel", "V2_error_rel", "HB_error_rel", "HT_error_rel")
PUNTOS_ESTRICTOS = {1, 2, 6, 45}

def verificacion_lineas(linea: str):
    s = linea.strip()
    if not s or s.startswith('-'):
        return False
    if s.lower().startswith('idx'):
        return False
    toks = s.split()
    if len(toks) != 5:
        return False
    return toks[0].isdigit()

def lectura_datos_archivos(ruta_txt: str):
    filas = []
    with open(ruta_txt, 'r', encoding='utf-8', errors='ignore') as f:
        for linea in f:
            if not verificacion_lineas(linea):
                continue
            toks = linea.split()
            idx = int(toks[0])
            try:
                v1 = float(toks[1]); v2 = float(toks[2]); hb = float(toks[3]); ht = float(toks[4])
            except ValueError:
                continue
            filas.append({
                'idx': idx,
                'V1_error_rel': v1,
                'V2_error_rel': v2,
                'HB_error_rel': hb,
                'HT_error_rel': ht,
            })
    return filas

def validaciones_errores_puntos(idx: int, valor: float):
    if idx in PUNTOS_ESTRICTOS:
        thr = 1e-3
        violado = not (valor < thr)
        regla = "valor < 1e-3"
    else:
        thr = 1e-2
        violado = valor > thr
        regla = "valor ≤ 1e-2"
    return violado, thr, regla

def verificar_archivo(ruta_txt: str):
    filas = lectura_datos_archivos(ruta_txt)
    violaciones = []
    for fila in filas:
        idx = fila['idx']
        for col in COLUMNAS:
            valor = fila[col]
            v, thr, regla = validaciones_errores_puntos(idx, valor)
            if v:
                violaciones.append({
                    'idx': idx,
                    'col': col,
                    'valor': valor,
                    'threshold': thr,
                    'regla': regla
                })
    return {'archivo': ruta_txt, 'violaciones': violaciones}

def analizar_resultados(carpeta_txt: str, patron="comparacion_*.txt", detener_si_hay_errores=False):
    rutas = sorted(glob.glob(os.path.join(carpeta_txt, patron)))
    reporte = []
    archivos_con_error = 0

    for ruta in rutas:
        res = verificar_archivo(ruta)
        reporte.append(res)
        if res['violaciones']:
            archivos_con_error += 1
            print(f"[ERROR] {os.path.basename(ruta)} — {len(res['violaciones'])} violación(es)")
            for v in res['violaciones']:
                print(f"   - idx={v['idx']:>4}  col={v['col']:<13}  valor={v['valor']:.6e}  "
                      f"umbral={v['threshold']:.1e}  (regla: {v['regla']})")
            if detener_si_hay_errores:
                raise ValueError(f"Se detectaron violaciones en {ruta}")
        else:
            print(f"[OK] {os.path.basename(ruta)} — sin violaciones")

    ok_total = (archivos_con_error == 0)
    print("\nResumen:")
    print(f"  Archivos analizados: {len(rutas)}")
    print(f"  Archivos con errores: {archivos_con_error}")
    print(f"  Estado general: {'OK' if ok_total else 'CON ERRORES'}")

    return ok_total, reporte

# ------------------- programa principal -------------------
if __name__ == "__main__":
# carpeta original
    ruta_a = r"D:\v06-run-pg"
# carpeta nueva
    ruta_b = r"D:\v07-run-2"
# carpeta salidas comparaciones
    ruta_salidas = r"C:\Users\Santo\OneDrive\Desktop\salidas_comparaciones_A"
# generar comparaciones
    generados = comparar_carpeta_a_vs_b(ruta_a, ruta_b, ruta_salidas, cantidad=80)
    print("Comparación completa")
    print("Archivos generados:", len(generados))
    for g in generados:
        print(" -", g)
# analizar errores en puntos criticos
    ok, reporte = analizar_resultados(ruta_salidas)
    if ok:
        print("Todos los archivos cumplen las tolerancias a los errores.")
    else:
        print("Se detectaron errores fuera de tolerancia establecida.")