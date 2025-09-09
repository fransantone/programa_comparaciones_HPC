import os
import re

_FLOAT = re.compile(r'^[+\-]?((\d+(\.\d*)?|\.\d+))([eE][+\-]?\d+)?$')

def float_number(line: str) -> bool:
    toks = line.strip().split()
    if not toks:
        return False
    return all(_FLOAT.match(t) and ('.' in t or 'e' in t.lower()) for t in toks)

def leer_registros(ruta_archivo): # Devuelve lista de tuplas (x, y, u, v, htot, h), una por 'línea lógica' (2 líneas reales).
    registros = []

    with open(ruta_archivo, 'r', encoding='utf-8') as f:
        lineas = f.readlines()

    lineas = lineas[2:]
    i = 0
    n = len(lineas)

    while i + 1 < n:
        l1 = lineas[i]
        l2 = lineas[i+1]
        if not (float_number(l1) and float_number(l2)):
            break
        a = list(map(float, l1.strip().split()))
        b = list(map(float, l2.strip().split()))
        if len(a) < 3 or len(b) < 3:
            break
        x, y, u = a[:3]
        v, htot, h = b[:3]
        registros.append((x, y, u, v, htot, h))
        i += 2
    print(registros)
    return registros

def comparar_registros(registros_a, registros_b): # Se crea un diccionario a partir de la comparacion de los registros guardados
    n = min(len(registros_a), len(registros_b))
    out = []
    for i in range(n):
        xa, ya, ua, va, hta, ha = registros_a[i]
        xb, yb, ub, vb, htb, hb = registros_b[i]
        out.append({
            "line": i+1,
            "x_diff":   xa - xb,
            "y_diff":   ya - yb,
            "u_diff":   ua - ub,
            "v_diff":   va - vb,
            "htot_diff":hta - htb,
            "h_diff":   ha - hb
        })
    return out

def formatear_txt(resultados): #Formato .txt del archivo de salida con las comparaciones
    bloques = []
    for r in resultados:
        bloques.append(f"Línea {r['line']}")
        bloques.append(
            f"x_diff: {r['x_diff']:.6e}  y_diff: {r['y_diff']:.6e}  u_diff: {r['u_diff']:.6e}"
        )
        bloques.append(
            f"v_diff: {r['v_diff']:.6e}  htot_diff: {r['htot_diff']:.6e}  h_diff: {r['h_diff']:.6e}\n"
        )
    return "\n".join(bloques).rstrip() + ("\n" if bloques else "")

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

def comparar_carpeta_a_vs_b(carpeta_a, carpeta_b, carpeta_salida, cantidad=80):
    os.makedirs(carpeta_salida, exist_ok=True)
    generados = []

    for i in range(1, cantidad+1):
        ruta_a = buscar_variantes(carpeta_a, i)
        ruta_b = buscar_variantes(carpeta_b, i)
        if not ruta_a or not ruta_b:
            # si falta alguno, seguimos
            continue

        regs_a = leer_registros(ruta_a)
        regs_b = leer_registros(ruta_b)
        res = comparar_registros(regs_a, regs_b)

        nombre_out = nombre_salida(os.path.basename(ruta_a))
        ruta_out = os.path.join(carpeta_salida, nombre_out)
        with open(ruta_out, "w", encoding="utf-8") as f:
            f.write(formatear_txt(res))
        generados.append(ruta_out)

    return generados

if __name__ == "__main__":
    ruta_a = r"D:\v06-run-pg"
    ruta_b = r"D:\v07-run-2"
    ruta_salidas = r"C:\Users\Santo\OneDrive\Desktop\salidas_comparaciones_A"

    generados = comparar_carpeta_a_vs_b(ruta_a, ruta_b, ruta_salidas, cantidad=80)
    print("Comparación completa")
    print("Archivos generados:", len(generados))
    for g in generados:
        print(" -", g)

