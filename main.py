import os
import re

_FLOAT = re.compile(r'^[+\-]?((\d+(\.\d*)?|\.\d+))([eE][+\-]?\d+)?$')

# ------------------- ayudantes -------------------
def _strip_comment(s: str) -> str:
    # corta lo que viene después de '#' o '!'
    for mark in ('#', '!'):
        p = s.find(mark)
        if p != -1:
            s = s[:p]
    return s

def _norm_token(tok: str) -> str:
    # Fortran D±exp -> E±exp ; coma decimal simple -> punto
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

# ------------------- CONFIG de comparación -------------------
# Variable sobre la que se calcula el error (cambiá a 'HB', 'V1' o 'V2' si querés)
ERROR_VAR = 'HT'

# ------------------- lectura de datos -------------------
def leer_registros(ruta_archivo):
    """
    Lee archivos con formato:
      NO  V1  V2  HT  HB
      ==  ==  ==  ==  ==
      <filas...>

    Devuelve un dict con 4 tuplas: {'V1':(...), 'V2':(...), 'HB':(...), 'HT':(...)}
    """
    V1, V2, HT, HB = [], [], [], []
    with open(ruta_archivo, "r", encoding="utf-8", errors="ignore") as f:
        lineas = f.readlines()

    # buscar encabezado de tabla
    i = 0
    while i < len(lineas) and not ("NO" in lineas[i] and "V1" in lineas[i] and "V2" in lineas[i] and "HT" in lineas[i] and "HB" in lineas[i]):
        i += 1
    if i == len(lineas):
        # si no hay encabezado esperado, devolvemos tuplas vacías
        return {'V1': tuple(), 'V2': tuple(), 'HB': tuple(), 'HT': tuple()}

    # saltar línea de "=="
    j = i + 1
    if j < len(lineas) and "=" in lineas[j]:
        j += 1

    # recorrer filas
    while j < len(lineas):
        s = _strip_comment(lineas[j]).strip()
        j += 1
        if not s:
            continue
        toks = s.split()
        if len(toks) < 5:
            continue
        try:
            # NO = toks[0] (índice) -> se ignora
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
def errores(a, b, eps=1e-15):
    """
    Calcula error absoluto y relativo:
      - err_abs = |a - b|
      - err_rel = err_abs / |a| si |a| > 0
                  err_abs si a == 0
    """
    abs_err = abs(a - b)
    if abs(a) > eps:
        rel_err = abs_err / abs(a)
    else:
        rel_err = abs_err  # cuando el original es 0, usamos el error absoluto
    return abs_err, rel_err

def compararaciones_numericas(tA, tB):
    """
    tA = ORIGINAL (dict con tuplas: 'V1','V2','HB','HT')
    tB = NUEVO    (dict con tuplas: 'V1','V2','HB','HT')

    Devuelve lista de dicts con:
      idx | V1_error_relativo | V2_error_relativo | HT_error_relativo | HB_error_relativo
    """
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
            "idx": i,  # si querés base 1: i+1
            "V1_error_relativo": v1_rel,
            "V2_error_relativo": v2_rel,
            "HT_error_relativo": ht_rel,
            "HB_error_relativo": hb_rel,
        })
    return out

# ------------------- salida .txt de comparaciones -------------------
def formatear_txt_detalle(resultados):
    """
    Tabla alineada con:
    idx | V1_error_relativo | V2_error_relativo | HT_error_relativo | HB_error_relativo
    """
    if not resultados:
        return "Sin datos\n"

    W = 18  # ancho de cada columna numérica
    header = (
        f"{'idx':>6}  "
        f"{'V1_error_relativo':>{W}}  "
        f"{'V2_error_relativo':>{W}}  "
        f"{'HT_error_relativo':>{W}}  "
        f"{'HB_error_relativo':>{W}}"
    )
    lineas = [header, "-" * len(header)]

    for r in resultados:
        lineas.append(
            f"{r['idx']:6d}  "
            f"{r['V1_error_relativo']:{W}.6e}  "
            f"{r['V2_error_relativo']:{W}.6e}  "
            f"{r['HT_error_relativo']:{W}.6e}  "
            f"{r['HB_error_relativo']:{W}.6e}"
        )
    return "\n".join(lineas) + "\n"

# ------------------- nombrado / búsqueda de archivos -------------------
# Acepta "chuS2.plt" y "chuS 2.plt"
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

if __name__ == "__main__":
    ruta_a = r"D:\v06-run-pg" # carpeta original
    ruta_b = r"D:\v07-run-2" # carpeta nueva
    ruta_salidas = r"C:\Users\Santo\OneDrive\Desktop\salidas_comparaciones_A"

    generados = comparar_carpeta_a_vs_b(ruta_a, ruta_b, ruta_salidas, cantidad=80)
    print("Comparación completa")
    print("Archivos generados:", len(generados))
    for g in generados:
        print(" -", g)
