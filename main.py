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


# ------------------- lectura de datos -------------------
def leer_todos_los_numeros(ruta_archivo):
    """
    Saltea las 2 primeras líneas (encabezado), corta comentarios,
    normaliza tokens y devuelve TODOS los números en una sola tupla (float).
    """
    nums = []
    with open(ruta_archivo, 'r', encoding='utf-8', errors='ignore') as f:
        lineas = f.readlines()
    lineas = lineas[2:]  # igual que venías haciendo
    for linea in lineas:
        s = _strip_comment(linea).strip()
        if not s:
            continue
        for tok in s.split():
            try:
                nums.append(float(_norm_token(tok)))
            except ValueError:
                pass
    return tuple(nums)


# ------------------- comparación numeoro a numero -------------------
def _errores(a, b, eps=1e-15):
    """
    Error absoluto: |a - b|
    Error relativo: ErrorAbs / |a|  (si |a|~0 y hay diferencia -> inf; si ambos ~0 -> 0)
    """
    abs_err = abs(a - b)
    den = abs(a)
    if den > eps:
        rel_err = abs_err / den
    else:
        rel_err = 0.0 if abs_err <= eps else float("inf")
    return abs_err, rel_err

def comparar_tuplas_planas(tA, tB):
    """
    tA = ORIGINAL (carpeta A) ; tB = NUEVO (carpeta B)
    Devuelve lista de dicts: idx, original, nuevo, err_abs, err_rel
    """
    n = min(len(tA), len(tB))
    out = []
    for i in range(n):
        a = tA[i]
        b = tB[i]
        ea, er = _errores(a, b)
        out.append({
            "idx": i,
            "original": a,
            "nuevo": b,
            "err_abs": ea,
            "err_rel": er,
        })
    return out


# ------------------- salida .txt de comparaciones -------------------
def formatear_txt_detalle(resultados):
    """
    Tabla en notación científica alineada y prolija.
    """
    if not resultados:
        return "Sin datos\n"

    # Encabezado
    header = f"{'idx':>6}  {'original':>15}  {'nuevo':>15}  {'err_abs':>15}  {'err_rel':>15}"
    lineas = [header, "-" * len(header)]

    # Filas en notación científica con ancho fijo
    for r in resultados:
        lineas.append(
            f"{r['idx']:6d}  "
            f"{r['original']:15.6e}  "
            f"{r['nuevo']:15.6e}  "
            f"{r['err_abs']:15.6e}  "
            f"{r['err_rel']:15.6e}"
        )
    return "\n".join(lineas) + "\n"

_NUM_CHU = re.compile(r'chu\s*([0-9]+)\.plt$', re.IGNORECASE)

def buscar_variantes(carpeta, i):
    for nombre in (f"chu{i}.plt", f"chu {i}.plt"):
        ruta = os.path.join(carpeta, nombre)
        if os.path.exists(ruta):
            return ruta
    return None

def nombre_salida(nombre_plt):
    m = _NUM_CHU.search(nombre_plt)
    if m:
        return f"comparacion_chu{m.group(1)}.txt"
    base = os.path.splitext(os.path.basename(nombre_plt))[0].replace(' ', '_')
    return f"comparacion_{base}.txt"



# ------------------- comparaciones de carpetas -------------------
def comparar_carpeta_a_vs_b(carpeta_a, carpeta_b, carpeta_salida, cantidad=80):
    """
    Compara chu1..chu{cantidad}.plt de carpeta_a (ORIGINAL) vs carpeta_b (NUEVO).
    Genera un .txt por par con detalle índice a índice.
    """
    os.makedirs(carpeta_salida, exist_ok=True)
    generados = []
    for i in range(1, cantidad+1):
        ruta_a = buscar_variantes(carpeta_a, i)
        ruta_b = buscar_variantes(carpeta_b, i)
        if not ruta_a or not ruta_b:
            continue
        tupla_A = leer_todos_los_numeros(ruta_a)
        tupla_B = leer_todos_los_numeros(ruta_b)
        resultados = comparar_tuplas_planas(tupla_A, tupla_B)
        ruta_out = os.path.join(carpeta_salida, nombre_salida(os.path.basename(ruta_a)))
        with open(ruta_out, "w", encoding="utf-8") as f:
            f.write(formatear_txt_detalle(resultados))
        generados.append(ruta_out)
        print(f"[OK] {os.path.basename(ruta_a)} vs {os.path.basename(ruta_b)}  "
              f"nA={len(tupla_A)}  nB={len(tupla_B)}  comparados={len(resultados)}  -> {ruta_out}")
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
