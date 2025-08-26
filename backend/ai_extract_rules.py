
# -*- coding: utf-8 -*-

"""
Regras de extração de valores do texto do PDF.
Uso:
    from ai_extract_rules import extract_values_from_text
    values, debug = extract_values_from_text(texto)
Retorno:
    values: dict com os campos reconhecidos
    debug:  str com explicações/trechos casados (útil para log)

Principais melhorias neste arquivo:
- Normalização automática de números no padrão brasileiro (vírgula decimal).
- Regra específica para 'pc_pump_depth' procurando valores próximos de
  menções a "bomba" ("BOMBA TUBULAR", "PARTE SUPERIOR DA BOMBA", etc).
- Interpretação de 2,441 como ID (não peso) quando aparecer no bloco OD/ID/COMP/PROFD.
- Regras mais tolerantes a quebras de linha e espaços.
"""


import re
from typing import Dict, Tuple

NUM = r'(?:\d{1,3}(?:[.\s]\d{3})*|\d+)(?:[.,]\d+)?'  # 1.234,56 | 1234,56 | 928,72 | 943.21

def _norm(s: str) -> str:
    """Converte vírgula decimal em ponto e remove separadores de milhar comuns."""
    if s is None:
        return s
    s = s.strip()
    # remove "." ou espaço usados como milhar
    s = re.sub(r'(?<=\d)[\s.](?=\d{3}\b)', '', s)
    s = s.replace(',', '.')
    return s

def _first(group):
    return group[0] if isinstance(group, (list, tuple)) and group else group

def extract_values_from_text(text: str) -> Tuple[Dict[str, str], str]:
    dbg = []
    values: Dict[str, str] = {}

    t = text

    # well name (ex.: SPT-115)
    m = re.search(r'\bSPT[-\s]?(\d+)\b', t, flags=re.I)
    if m:
        values["well_name"] = f"SPT-{m.group(1)}"
        dbg.append(f"well_name => {values['well_name']}")

    # TUBING OD/ID a partir do bloco OD / ID / COMP / PROFD
    od = re.search(r'\bOD\s*('+NUM+')', t, flags=re.I)
    if od:
        values["tubing_od"] = _norm(od.group(1))
        dbg.append(f"tubing_od => {values['tubing_od']} (OD)")
    tubing_id = re.search(r'\bID\s*('+NUM+')', t, flags=re.I)
    if tubing_id:
        values["tubing_id"] = _norm(tubing_id.group(1))
        dbg.append(f"tubing_id => {values['tubing_id']} (ID)")
        if "tubing_weight" in values:
            del values["tubing_weight"]

    comp = re.search(r'\bCOMP(?:ETENCIA|)?\s*('+NUM+')', t, flags=re.I)
    letdown = re.search(r'LET\s*DOWN\s*('+NUM+')', t, flags=re.I)
    if comp:
        values["tubing_avg_joint_length"] = _norm(comp.group(1))
        dbg.append(f"tubing_avg_joint_length => {values['tubing_avg_joint_length']} (COMP)")
    elif letdown:
        values["tubing_avg_joint_length"] = _norm(letdown.group(1))
        dbg.append(f"tubing_avg_joint_length => {values['tubing_avg_joint_length']} (LET DOWN)")

    # Profundidades (PROFD). Primeiro como topo, último como fundo.
    profds = re.findall(r'\bPROFD\s*('+NUM+')', t, flags=re.I)
    if profds:
        normed = [ _norm(x) for x in profds ]
        try:
            normed_f = [ float(x) for x in normed ]
            topo_val = min(normed_f)
            fundo_val = max(normed_f)
            values["tubing_top"] = f"{topo_val:.2f}".rstrip('0').rstrip('.')
            values["tubing_bottom"] = f"{fundo_val:.2f}".rstrip('0').rstrip('.')
            dbg.append(f"tubing_top => {values['tubing_top']} / tubing_bottom => {values['tubing_bottom']} (PROFD)")
        except Exception:
            values["tubing_top"] = normed[0]
            values["tubing_bottom"] = normed[-1]
            dbg.append(f"tubing_top => {values['tubing_top']} / tubing_bottom => {values['tubing_bottom']} (PROFD fallback)")

    # Haste polida (rod string)
    m = re.search(r'HASTE\s+POLIDA\s+([0-9\s/"]+)', t, flags=re.I)
    if m:
        values["rod_string"] = m.group(1).strip()
        dbg.append(f"rod_string => {values['rod_string']}")

    # PC Pump Depth — procurar perto de 'BOMBA'
    bomba_blk = re.search(
        r'(?is)(?:BOMBA(?:\s+TUBULAR)?|PARTE\s+SUPERIOR\s+DA\s+BOMBA)[\s\S]{0,200}?('+NUM+')',
        t
    )
    if bomba_blk:
        values["pc_pump_depth"] = _norm(bomba_blk.group(1))
        dbg.append(f"pc_pump_depth => {values['pc_pump_depth']} (próximo de 'BOMBA')")
    else:
        odidblk = re.search(
            r'(?is)\bOD\s*'+NUM+r'.{0,80}\bID\s*'+NUM+r'.{0,80}\bCOMP\s*'+NUM+r'.{0,80}\bPROFD\s*('+NUM+')',
            t
        )
        if odidblk:
            values["pc_pump_depth"] = _norm(odidblk.group(1))
            dbg.append(f"pc_pump_depth => {values['pc_pump_depth']} (fallback bloco OD/ID/COMP/PROFD)")

    # Tubing OD textual (ex.: "TUBOS DE PRODUÇÃO 2 7/8'' EU")
    m = re.search(r'TUBOS\s+DE\s+PRODU[ÇC][AÃ]O\s+([0-9\s/]+)"', t, flags=re.I)
    if m and "tubing_od" not in values:
        values["tubing_od"] = m.group(1).strip()
        dbg.append(f"tubing_od => {values['tubing_od']} (texto)")

    # Correção de 2,441 usado como "weight"
    if values.get("tubing_weight") in {"2,441", "2.441"}:
        values["tubing_id"] = values.pop("tubing_weight")
        dbg.append("Corrigido: tubing_weight (2,441) reconhecido como tubing_id.")

    return values, "\n".join(dbg)
